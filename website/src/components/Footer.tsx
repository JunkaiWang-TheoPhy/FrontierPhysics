import { Button } from "@/components/ui/button";
import { DiscordIcon } from "@/components/BrandIcon";
import { site } from "@/lib/site";
import { Github } from "lucide-react";
import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border bg-muted mt-24">
      <div className="max-w-5xl mx-auto px-4 md:px-8 py-12">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-8 mb-8">
          <div>
            <h3 className="font-normal mb-4 flex items-center gap-2">
              {site.name}
              <span className="w-2 h-2 bg-primary rounded-full" />
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
              An open benchmark measuring whether AI agents can do real physics
              research.
            </p>
          </div>

          <div className="flex gap-12">
            <div>
              <h4 className="font-semibold mb-4 text-sm">Resources</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link
                    href="/contribute"
                    className="hover:text-foreground transition-colors"
                  >
                    Contribute a task
                  </Link>
                </li>
                <li>
                  <a
                    href={site.protocol}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground transition-colors"
                  >
                    Benchmark protocol
                  </a>
                </li>
                <li>
                  <a
                    href={site.taxonomy}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground transition-colors"
                  >
                    Taxonomy
                  </a>
                </li>
                <li>
                  <a
                    href={site.benchflow}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground transition-colors"
                  >
                    BenchFlow SDK
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold mb-4 text-sm">Community</h4>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  asChild
                  className="h-9 w-9"
                  aria-label="GitHub"
                >
                  <a href={site.repo} target="_blank" rel="noopener noreferrer">
                    <Github className="w-5 h-5" aria-hidden="true" />
                  </a>
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  asChild
                  className="h-9 w-9"
                  aria-label="Discord"
                >
                  <a
                    href={site.discord}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <DiscordIcon className="w-5 h-5" aria-hidden="true" />
                  </a>
                </Button>
              </div>
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-border">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} {site.name} · Built by the{" "}
            <a
              href="https://www.benchflow.ai/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              BenchFlow
            </a>{" "}
            team, also behind{" "}
            <a
              href={site.skillsbenchPaper}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              SkillsBench
            </a>{" "}
            · Open source under the Apache 2.0 License
          </p>
        </div>
      </div>
    </footer>
  );
}
