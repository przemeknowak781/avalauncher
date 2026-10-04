// Run the demo engine (web/engine.js) on web/data and print flags + flight plan for one morning as JSON,
// so the concept render shows exactly what the demo screen shows.
// Usage: node tools/visuals/engine_flags.mjs [dayIndex=1] [budgetMin=20] > flags.json
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const { assess, planFlight } = await import(pathToFileURL(join(root, "web", "engine.js")).href);
const j = (p) => JSON.parse(readFileSync(join(root, "web", "data", p), "utf8"));
const DAYS = j("days.json");
const sectors = j("sectors.json");
const scenarios = j("scenarios.json");
const trails = j("trails.json");
const ctx = { exposure: DAYS.exposure, base: DAYS.base, scenarios, trails };
const di = Number(process.argv[2] ?? 1);
const budget = Number(process.argv[3] ?? 20);
const day = DAYS.days[di];
const flags = assess(day, sectors, ctx);
const plan = planFlight(day, sectors, flags, budget, ctx);
process.stdout.write(JSON.stringify({ day: day.id, label: day.label, status: day.status, weather: day.weather, base: DAYS.base, flags, plan, library_count: scenarios.count }, null, 1));
