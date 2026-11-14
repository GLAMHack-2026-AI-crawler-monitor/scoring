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
    label: "Synthetic_data_stress_test_sample_(999_requests_and_120_IP_adresses)",
    file: FileAttachment("data/ip_scores_sample.csv")
  },
  {
    id: "crawler_monitor_sample",
    label: "GLAMhack_anonymized_data_sample_with_fixed_IP_ranges_(14599_requests_and _157_IP_adresses)",
    file: FileAttachment("data/ip_scores_crawler_monitor_sample.csv")
  }
];
