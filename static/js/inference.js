const OikosModel = (() => {
  const MODEL_URL = "/static/model/oikos-rf-v1.json";
  const BINARY_URL = "/static/model/oikos-rf-v1.bin";
  const SECTION_SIZES = {
    feature: 1,
    left: 4,
    right: 4,
    threshold: 8,
    value: 8,
  };

  let modelPromise = null;

  function toArrayBuffer(value) {
    if (value instanceof ArrayBuffer) return value;
    return value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength);
  }

  function createModel(metadata, source) {
    if (!metadata || metadata.format_version !== 1) {
      throw new Error("Formato de modelo no soportado");
    }

    const buffer = toArrayBuffer(source);
    const view = new DataView(buffer);
    const sections = metadata.sections || {};

    Object.entries(SECTION_SIZES).forEach(([name, size]) => {
      const section = sections[name];
      if (!section) throw new Error(`Falta la sección ${name}`);
      const end = section.offset + section.length * size;
      if (section.offset < 0 || end > buffer.byteLength) {
        throw new Error(`Sección ${name} fuera de rango`);
      }
    });

    if (metadata.tree_node_offsets.length !== metadata.n_trees + 1) {
      throw new Error("Índices de árboles inválidos");
    }

    return {
      metadata,
      view,
      zonaIndex: new Map(metadata.zona_classes.map((value, index) => [value, index])),
      ciudadIndex: new Map(
        metadata.ciudad_classes.map((value, index) => [value, index]),
      ),
    };
  }

  function buildFeatures(model, data) {
    const ambientes = Number(data.ambientes);
    const bathrooms = Number(data.bathrooms);
    const area = Number(data.area);

    if (!Number.isFinite(ambientes) || ambientes <= 0) {
      throw new Error("Ambientes inválidos");
    }
    if (!Number.isFinite(bathrooms) || bathrooms < 0) {
      throw new Error("Baños inválidos");
    }
    if (!Number.isFinite(area) || area <= 0) {
      throw new Error("Área inválida");
    }

    const zona = model.zonaIndex.get(data.zona);
    const ciudad = model.ciudadIndex.get(data.ciudad);
    if (zona === undefined || ciudad === undefined) {
      throw new Error("Zona o ciudad no reconocida");
    }

    const values = {
      ambientes,
      bathrooms,
      area,
      ambientes_por_m2: ambientes / area,
      "baños_por_ambiente": bathrooms / ambientes,
      zona_encoded: zona,
      ciudad_encoded: ciudad,
    };

    return model.metadata.feature_names.map((name) => {
      const value = values[name];
      if (!Number.isFinite(value)) throw new Error(`Feature inválida: ${name}`);
      return value;
    });
  }

  function predictWithFeatures(model, features) {
    const { metadata, view } = model;
    const { feature, left, right, threshold, value } = metadata.sections;

    if (features.length !== metadata.n_features) {
      throw new Error("Cantidad de features inválida");
    }

    let sum = 0;

    for (let tree = 0; tree < metadata.n_trees; tree += 1) {
      let node = metadata.tree_node_offsets[tree];
      const end = metadata.tree_node_offsets[tree + 1];

      while (node < end) {
        const leftChild = view.getInt32(left.offset + node * 4, true);
        if (leftChild === -1) break;
        const featureIndex = view.getUint8(feature.offset + node);
        const split = view.getFloat64(threshold.offset + node * 8, true);
        const rightChild = view.getInt32(right.offset + node * 4, true);
        node = features[featureIndex] <= split ? leftChild : rightChild;
      }

      sum += view.getFloat64(value.offset + node * 8, true);
    }

    return sum / metadata.n_trees;
  }

  function predictFromModel(model, data) {
    return predictWithFeatures(model, buildFeatures(model, data));
  }

  function formatUSD(price) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(price);
  }

  async function loadModel() {
    if (!modelPromise) {
      modelPromise = Promise.all([
        fetch(MODEL_URL, { cache: "force-cache" }).then((response) => {
          if (!response.ok) throw new Error(`Error HTTP ${response.status}`);
          return response.json();
        }),
        fetch(BINARY_URL, { cache: "force-cache" }).then((response) => {
          if (!response.ok) throw new Error(`Error HTTP ${response.status}`);
          return response.arrayBuffer();
        }),
      ])
        .then(([metadata, buffer]) => createModel(metadata, buffer))
        .catch((error) => {
          modelPromise = null;
          throw error;
        });
    }

    return modelPromise;
  }

  async function predictPrice(data) {
    const model = await loadModel();
    const predictedPrice = predictFromModel(model, data);
    return {
      predicted_price: predictedPrice,
      formatted_price: formatUSD(predictedPrice),
    };
  }

  const api = {
    MODEL_URL,
    BINARY_URL,
    loadModel,
    createModel,
    buildFeatures,
    predictWithFeatures,
    predictFromModel,
    predictPrice,
    formatUSD,
  };

  if (typeof window !== "undefined") window.OikosModel = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;

  return api;
})();
