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
  CLAUDE_CODE_OAUTH_TOKEN
)
for name in "${required[@]}"; do
  if [ -z "${!name:-}" ]; then
    echo "sandbox configuration is incomplete" >&2
    exit 1
  fi
done

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
  "$workspace/ai_detection.json"; do
  if [ ! -f "$path" ] || [ -L "$path" ]; then
    echo "sandbox review input is missing or unsafe" >&2
    exit 1
  fi
done

command -v bwrap > /dev/null

# Older supported Bubblewrap builds do not have --clearenv. Build an explicit
# scrub list from names only, retaining exactly the OAuth credential. The token
# remains inherited environment data and is never placed in a process argument.
env_scrub=()
oauth_seen=false
exec {environment_fd}< <(/usr/bin/env -0)
environment_pid=$!
while IFS= read -r -d '' entry <&"$environment_fd"; do
  name=${entry%%=*}
  if [ "$name" = "CLAUDE_CODE_OAUTH_TOKEN" ]; then
    oauth_seen=true
  elif [[ "$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    env_scrub+=(--unsetenv "$name")
  else
    echo "sandbox environment contains an invalid variable name" >&2
    exit 1
  fi
done
exec {environment_fd}<&-
if ! wait "$environment_pid" || [ "$oauth_seen" != "true" ]; then
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
  --dir /etc/ssl
  --ro-bind-try /etc/ssl/certs /etc/ssl/certs
  --ro-bind-try /etc/ca-certificates.conf /etc/ca-certificates.conf
  --ro-bind-try /etc/resolv.conf /etc/resolv.conf
  --ro-bind-try /etc/hosts /etc/hosts
  --ro-bind-try /etc/nsswitch.conf /etc/nsswitch.conf
  --ro-bind-try /etc/gai.conf /etc/gai.conf
  --ro-bind-try /etc/passwd /etc/passwd
  --ro-bind-try /etc/group /etc/group
  --ro-bind-try /etc/os-release /etc/os-release
  --ro-bind-try /etc/localtime /etc/localtime
  --dir /opt
  --ro-bind "$claude_root" /opt/claude
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

# The native Claude runtime requires procfs during startup. The workflow makes
# it unreachable to model-controlled tools: Bash/Grep/Glob are absent, Read is
# allowlisted to review inputs, and an absolute //proc/** deny takes precedence.
exec bwrap \
  --die-with-parent \
  --new-session \
  --unshare-user \
  --unshare-pid \
  --unshare-ipc \
  --unshare-uts \
  --unshare-cgroup-try \
  --cap-drop ALL \
  --proc /proc \
  --dev /dev \
  --tmpfs /tmp \
  "${mounts[@]}" \
  "${env_scrub[@]}" \
  --chdir /workspace \
  --setenv HOME /home/claude \
  --setenv USER claude \
  --setenv LOGNAME claude \
  --setenv PATH /usr/local/bin:/usr/bin:/bin \
  --setenv LANG C.UTF-8 \
  --setenv LC_ALL C.UTF-8 \
  --setenv TMPDIR /tmp \
  --setenv CI true \
  --setenv GITHUB_ACTIONS true \
  --setenv GITHUB_WORKSPACE /workspace \
  --setenv CLAUDE_CODE_ENTRYPOINT "${CLAUDE_CODE_ENTRYPOINT:-claude-code-github-action}" \
  --setenv CLAUDE_CODE_SUBPROCESS_ENV_SCRUB 0 \
  /opt/claude/node_modules/@anthropic-ai/claude-code/bin/claude.exe "$@"
