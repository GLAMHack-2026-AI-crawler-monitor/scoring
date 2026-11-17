#!/usr/bin/env node
// Data loader (see https://observablehq.com/framework/loaders): Framework
// runs this at dev/build time and its stdout becomes docs/scoring.md (served
// as the "/scoring" page), so the dashboard always shows the same content as
// the canonical ../../docs/scoring.md instead of a hand-copied page that can
// drift out of sync. No rewriting is needed: Framework treats ```mermaid
// fences as a built-in tag, same as GitHub.
import {readFile} from "node:fs/promises";

const source = await readFile(new URL("../../docs/scoring.md", import.meta.url), "utf8");

process.stdout.write(source);
