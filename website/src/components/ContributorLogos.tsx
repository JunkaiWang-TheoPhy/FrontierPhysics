import "./ContributorLogos.css";

/** Marks live in public/, which basePath does not prefix automatically. */
const ASSET_BASE = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/logos`;

/**
 * Contributor institutions, most influential first, deduped across the
 * contributor roster and the core-author list. Heights are tuned per mark so
 * wide wordmarks and round seals carry the same optical weight in the row.
 */
const INSTITUTIONS = [
  { file: "stanford.svg", name: "Stanford University", height: 44 },
  { file: "uc-berkeley.svg", name: "UC Berkeley", height: 44 },
  { file: "caltech.svg", name: "Caltech", height: 44 },
  { file: "cmu.svg", name: "Carnegie Mellon University", height: 44 },
  { file: "tsinghua.svg", name: "Tsinghua University", height: 44 },
  { file: "georgia-tech.svg", name: "Georgia Institute of Technology", height: 44 },
  { file: "uw.svg", name: "University of Washington", height: 44 },
  { file: "uiuc.svg", name: "University of Illinois Urbana-Champaign", height: 44 },
  { file: "ut-austin.svg", name: "The University of Texas at Austin", height: 44 },
  { file: "ucsd.svg", name: "UC San Diego", height: 44 },
  { file: "amazon.svg", name: "Amazon", height: 30 },
  { file: "berkeley-lab.svg", name: "Lawrence Berkeley National Laboratory", height: 32 },
  { file: "argonne.svg", name: "Argonne National Laboratory", height: 34 },
  { file: "sjtu.png", name: "Shanghai Jiao Tong University", height: 44 },
  { file: "nanjing.svg", name: "Nanjing University", height: 44 },
  { file: "hku.png", name: "The University of Hong Kong", height: 44 },
  { file: "cuhk-shenzhen.png", name: "The Chinese University of Hong Kong, Shenzhen", height: 44 },
  { file: "northeastern.png", name: "Northeastern University", height: 44 },
  { file: "temple.svg", name: "Temple University", height: 44 },
  { file: "benchflow.png", name: "BenchFlow", height: 36 },
] as const;

export function ContributorLogos() {
  return (
    <section aria-label="Contributor institutions" className="py-8">
      <div className="logo-marquee">
        <div className="logo-marquee-track">
          {/* The second copy exists only to make the loop seamless. */}
          {[0, 1].map((copy) => (
            <ul
              key={copy}
              className="logo-marquee-group"
              aria-hidden={copy === 1 || undefined}
            >
              {INSTITUTIONS.map((inst) => (
                <li key={inst.file}>
                  {/* Not lazy: with width:auto an unloaded image has zero
                      area, so it never intersects and lazy never fires. */}
                  {/* eslint-disable-next-line @next/next/no-img-element -- static marks; no optimizer pass wanted */}
                  <img
                    src={`${ASSET_BASE}/${inst.file}`}
                    alt={inst.name}
                    title={inst.name}
                    style={{ height: inst.height }}
                    className="contributor-logo"
                  />
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>
    </section>
  );
}
