import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const require = createRequire(import.meta.url);
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const OikosModel = require(resolve(root, "static/js/inference.js"));

const metadata = JSON.parse(
  readFileSync(resolve(root, "static/model/oikos-rf-v1.json"), "utf8"),
);
const binary = readFileSync(resolve(root, "static/model/oikos-rf-v1.bin"));
const fixtures = JSON.parse(
  readFileSync(resolve(root, "tests/model_fixtures.json"), "utf8"),
);

const model = OikosModel.createModel(metadata, new Uint8Array(binary));
let failed = false;

for (const fixture of fixtures.cases) {
  const features = OikosModel.buildFeatures(model, fixture.input);
  const featureDelta = Math.max(
    ...features.map((value, index) => Math.abs(value - fixture.features[index])),
  );
  const actual = OikosModel.predictFromModel(model, fixture.input);
  const priceDelta = Math.abs(actual - fixture.expected_price);
  const ok = featureDelta < 1e-12 && priceDelta < 0.5;

  console.log(
    `${ok ? "OK " : "FAIL"} ${fixture.input.zona} / ${fixture.input.ciudad} ` +
      `esperado=${fixture.expected_price.toFixed(2)} ` +
      `obtenido=${actual.toFixed(2)} delta=${priceDelta.toFixed(4)}`,
  );

  if (!ok) failed = true;
}

if (failed) process.exit(1);
