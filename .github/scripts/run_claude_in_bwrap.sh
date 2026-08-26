#!/usr/bin/env bash
# Run Claude Code inside a filesystem-minimal Bubblewrap sandbox.
#
# The GitHub Action SDK remains on the runner host, but every model-controlled
# tool (including the in-process Read and Skill tools) lives in this wrapped
# CLI process.

set -euo pipefail

required=(
  GITHUB_WORKSPACE
  RUNNER_TEMP
  GITHUB_RUN_ID
  GITHUB_RUN_ATTEMPT
  SANDBOX_CLAUDE_ROOT
  SANDBOX_AGENT_HOME
)
for name in "${required[@]}"; do
  if [ -z "${!name:-}" ]; then
    echo "sandbox configuration is incomplete" >&2
    exit 1
  fi
done

review_mode=true
oauth_token=""
if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then
  # The credential-free install step uses this exact preflight. All other
  # invocations are the pinned Agent SDK review path and require OAuth.
  review_mode=false
elif [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  echo "sandbox review credential is missing" >&2
  exit 1
else
  # Keep the credential in shell memory, but remove it from the exported
  # environment before invoking any setup helper. It is reintroduced only for
  # the final Bubblewrap process and never placed in argv.
  oauth_token=$CLAUDE_CODE_OAUTH_TOKEN
fi
unset CLAUDE_CODE_OAUTH_TOKEN

case "$GITHUB_RUN_ID:$GITHUB_RUN_ATTEMPT" in
  *[!0-9:]*|:*|*:) echo "sandbox run identity is invalid" >&2; exit 1 ;;
esac

workspace=$(realpath -e -- "$GITHUB_WORKSPACE")
runner_temp=$(realpath -e -- "$RUNNER_TEMP")
claude_root=$(realpath -e -- "$SANDBOX_CLAUDE_ROOT")
agent_home=$(realpath -e -- "$SANDBOX_AGENT_HOME")
expected_cli_root="$runner_temp/claude-cli-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
expected_agent_home="$runner_temp/claude-home-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
if [ "$claude_root" != "$expected_cli_root" ] || [ "$agent_home" != "$expected_agent_home" ]; then
  echo "sandbox paths are not bound to this workflow attempt" >&2
  exit 1
fi

host_cli="$claude_root/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
if [ ! -x "$host_cli" ] || [ -L "$host_cli" ]; then
  echo "pinned Claude executable is missing or unsafe" >&2
  exit 1
fi

for path in \
  "$workspace/.agents/skills/task-review" \
  "$workspace/.github/agent-review" \
  "$workspace/pr-head" \
  "$workspace/pr-head-scripts-as-submitted"; do
  if [ ! -d "$path" ] || [ -L "$path" ]; then
    echo "sandbox review directory is missing or unsafe" >&2
    exit 1
  fi
done
for path in \
  "$workspace/CONTRIBUTING.md" \
  "$workspace/taxonomy.md" \
  "$workspace/changed_files.json" \
  "$workspace/review_files.json" \
  "$workspace/pr_meta.json" \
  "$workspace/advisory_checks.txt" \
  "$workspace/ai_detection.json" \
  "$workspace/.github/agent-review/managed-settings.json" \
  "$workspace/.github/scripts/claude_egress_proxy.py" \
  "$workspace/.github/scripts/validate_agent_review_security.py"; do
  if [ ! -f "$path" ] || [ -L "$path" ]; then
    echo "sandbox review input is missing or unsafe" >&2
    exit 1
  fi
done

command -v bwrap > /dev/null
if [ ! -x /usr/bin/python3 ]; then
  echo "sandbox Python runtime is unavailable" >&2
  exit 1
fi
/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 \
  /usr/bin/python3 -I "$workspace/.github/scripts/validate_agent_review_security.py" \
  --repo-root "$workspace" > /dev/null

# Older supported Bubblewrap builds do not have --clearenv. Build an explicit
# scrub list from names only. The exported environment contains no credential;
# review mode reintroduces it only when launching the final Bubblewrap process.
env_scrub=()
exec {environment_fd}< <(/usr/bin/env -0)
environment_pid=$!
while IFS= read -r -d '' entry <&"$environment_fd"; do
  name=${entry%%=*}
  if [[ "$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    env_scrub+=(--unsetenv "$name")
  else
    echo "sandbox environment contains an invalid variable name" >&2
    exit 1
  fi
done
exec {environment_fd}<&-
if ! wait "$environment_pid"; then
  echo "sandbox environment enumeration was incomplete" >&2
  exit 1
fi

mounts=(
  --ro-bind /usr /usr
  --ro-bind /bin /bin
  --ro-bind /lib /lib
  --ro-bind-try /lib64 /lib64
  --ro-bind-try /sbin /sbin
  --dir /etc
  --dir /etc/claude-code
  --ro-bind "$workspace/.github/agent-review/managed-settings.json" /etc/claude-code/managed-settings.json
  --dir /etc/ssl
  --ro-bind-try /etc/ssl/certs /etc/ssl/certs
  --ro-bind-try /etc/ca-certificates.conf /etc/ca-certificates.conf
  --ro-bind-try /etc/passwd /etc/passwd
  --ro-bind-try /etc/group /etc/group
  --ro-bind-try /etc/os-release /etc/os-release
  --ro-bind-try /etc/localtime /etc/localtime
  --dir /opt
  --ro-bind "$claude_root" /opt/claude
  --ro-bind "$workspace/.github/scripts/claude_egress_proxy.py" /opt/claude-egress-proxy.py
  --dir /home
  --bind "$agent_home" /home/claude
  --dir /workspace
  --dir /workspace/.agents
  --dir /workspace/.agents/skills
  --ro-bind "$workspace/.agents/skills/task-review" /workspace/.agents/skills/task-review
  --dir /workspace/.claude
  --dir /workspace/.claude/skills
  --ro-bind "$workspace/.agents/skills/task-review" /workspace/.claude/skills/task-review
  --dir /workspace/.github
  --ro-bind "$workspace/.github/agent-review" /workspace/.github/agent-review
  --ro-bind "$workspace/CONTRIBUTING.md" /workspace/CONTRIBUTING.md
  --ro-bind "$workspace/taxonomy.md" /workspace/taxonomy.md
  --ro-bind "$workspace/pr-head" /workspace/pr-head
  --ro-bind "$workspace/pr-head-scripts-as-submitted" /workspace/pr-head-scripts-as-submitted
  --ro-bind "$workspace/changed_files.json" /workspace/changed_files.json
  --ro-bind "$workspace/review_files.json" /workspace/review_files.json
  --ro-bind "$workspace/pr_meta.json" /workspace/pr_meta.json
  --ro-bind "$workspace/advisory_checks.txt" /workspace/advisory_checks.txt
  --ro-bind "$workspace/ai_detection.json" /workspace/ai_detection.json
)

proxy_pid=""
proxy_dir=""
cleanup_proxy() {
  if [ -n "$proxy_pid" ]; then
    kill "$proxy_pid" 2> /dev/null || true
    wait "$proxy_pid" 2> /dev/null || true
  fi
  if [ -n "$proxy_dir" ]; then
    rmdir -- "$proxy_dir" 2> /dev/null || true
  fi
}

if [ "$review_mode" = "true" ]; then
  proxy_dir="$runner_temp/ce-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
  if [ -e "$proxy_dir" ] || [ -L "$proxy_dir" ]; then
    echo "sandbox egress directory already exists" >&2
    exit 1
  fi
  (umask 077 && mkdir -- "$proxy_dir")
  if [ "$(realpath -e -- "$proxy_dir")" != "$proxy_dir" ]; then
    echo "sandbox egress directory is unsafe" >&2
    exit 1
  fi
  proxy_socket="$proxy_dir/proxy.sock"
  proxy_ready="$proxy_dir/ready"
  trap cleanup_proxy EXIT
  # The host-side proxy needs network access but no credentials. Start it with
  # an empty environment so the OAuth and GitHub tokens remain only in the
  # wrapped Claude process and its trusted caller.
  /usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    /usr/bin/python3 -I "$workspace/.github/scripts/claude_egress_proxy.py" \
    serve --socket "$proxy_socket" --ready-file "$proxy_ready" &
  proxy_pid=$!
  proxy_is_ready=false
  for _ in $(seq 1 100); do
    if [ -f "$proxy_ready" ] && kill -0 "$proxy_pid" 2> /dev/null; then
      proxy_is_ready=true
      break
    fi
    if ! kill -0 "$proxy_pid" 2> /dev/null; then
      break
    fi
    sleep 0.05
  done
  if [ "$proxy_is_ready" != "true" ]; then
    echo "sandbox egress proxy failed to start" >&2
    exit 1
  fi
  mounts+=(
    --dir /run
    --ro-bind "$proxy_dir" /run/claude-egress
  )
fi

# The native Claude runtime requires procfs during startup. The managed policy
# and CLI arguments independently limit tools to Read and Skill. Network access
# is kernel-denied by --unshare-net; review mode can reach only the mounted Unix
# socket, whose host proxy accepts exact Anthropic CONNECT authorities.
bwrap_args=(
  --die-with-parent
  --new-session
  --unshare-user
  --unshare-pid
  --unshare-ipc
  --unshare-uts
  --unshare-net
  --unshare-cgroup-try
  --cap-drop ALL
  --proc /proc
  --dev /dev
  --tmpfs /tmp
  "${mounts[@]}"
  "${env_scrub[@]}"
  --chdir /workspace
  --setenv HOME /home/claude
  --setenv USER claude
  --setenv LOGNAME claude
  --setenv PATH /usr/local/bin:/usr/bin:/bin
  --setenv LANG C.UTF-8
  --setenv LC_ALL C.UTF-8
  --setenv TMPDIR /tmp
  --setenv CI true
  --setenv GITHUB_ACTIONS true
  --setenv GITHUB_WORKSPACE /workspace
  --setenv CLAUDE_CODE_ENTRYPOINT "${CLAUDE_CODE_ENTRYPOINT:-claude-code-github-action}"
  --setenv CLAUDE_CODE_SUBPROCESS_ENV_SCRUB 1
  --setenv CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 1
  --setenv ENABLE_CLAUDEAI_MCP_SERVERS false
  --setenv CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL 1
  --setenv CLAUDE_CODE_DISABLE_ARTIFACT 1
  --setenv DISABLE_AUTOUPDATER 1
)

if [ "$review_mode" != "true" ]; then
  exec bwrap "${bwrap_args[@]}" \
    /opt/claude/node_modules/@anthropic-ai/claude-code/bin/claude.exe "$@"
fi

bwrap_args+=(
  --setenv HTTPS_PROXY http://127.0.0.1:3128
  --setenv HTTP_PROXY http://127.0.0.1:3128
  --setenv https_proxy http://127.0.0.1:3128
  --setenv http_proxy http://127.0.0.1:3128
  --setenv NO_PROXY ""
  --setenv no_proxy ""
)

set +e
CLAUDE_CODE_OAUTH_TOKEN="$oauth_token" bwrap "${bwrap_args[@]}" \
  /usr/bin/python3 -I /opt/claude-egress-proxy.py \
  relay --socket /run/claude-egress/proxy.sock \
  --listen-host 127.0.0.1 --listen-port 3128 -- \
  /opt/claude/node_modules/@anthropic-ai/claude-code/bin/claude.exe "$@"
status=$?
set -e
exit "$status"
