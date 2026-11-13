// The list of datasets shown in the dashboard lives here (not in a plain
// JSON config) because Observable Framework resolves file dependencies by
// statically scanning the source for literal FileAttachment("...") calls, so
// a path read out of a JSON config can't become a FileAttachment at runtime
// — each entry below must call FileAttachment() with its path written out
// literally. To add a new dataset: run score_bot_ips.py to produce
// `ip_scores_<name>.csv`, symlink it into docs/data/, and add an entry here.
//
// FileAttachment is a markdown-block global in Framework pages, but plain
// imported JS modules like this one need to import it explicitly.
import {FileAttachment} from "npm:@observablehq/stdlib";

export const DATASETS = [
  {
    id: "sample",
    label: "Synthetic stress-test sample (999 requests, 120 IPs)",
    file: FileAttachment("data/ip_scores_sample.csv")
  }
];
