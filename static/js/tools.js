// Manejo del selector de ubicación
function initLocationSelectors() {
  const regionSelect = document.getElementById("region-select");
  const localidadSelect = document.getElementById("localidad-select");

  if (!regionSelect || !localidadSelect) return;

  regionSelect.addEventListener("change", function () {
    const regionSeleccionada = this.value;

    // Limpiar localidades
    localidadSelect.innerHTML = '<option value="">Select city...</option>';

    if (regionSeleccionada && UBICACIONES[regionSeleccionada]) {
      // Habilitar el select de localidad
      localidadSelect.disabled = false;

      // Agregar las localidades de la región seleccionada
      UBICACIONES[regionSeleccionada].forEach((item) => {
        const option = document.createElement("option");
        option.value = item.value;
        option.textContent = item.label;
        localidadSelect.appendChild(option);
      });
    } else {
      localidadSelect.disabled = true;
    }
  });

  localidadSelect.addEventListener("change", function () {
    const region = regionSelect.value;
    const localidad = this.value;

    if (region && localidad) {
      console.log(`Ubicación seleccionada: ${region} - ${localidad}`);
      // Aquí puedes agregar lógica adicional cuando se seleccione una localidad
    }
  });
}

// Manejo de herramientas (checkboxes)
function initTools() {
  function handleSingleCheckbox(containerSelector) {
    const container = document.querySelector(containerSelector);
    container.addEventListener("change", (e) => {
      if (e.target.type === "checkbox") {
        container
          .querySelectorAll('input[type="checkbox"]')
          .forEach((checkbox) => {
            if (checkbox !== e.target) checkbox.checked = false;
          });
      }
    });
  }
  // Solo permitir un checkbox activo a la vez
  handleSingleCheckbox(".sidebar-left");
  handleSingleCheckbox(".floors");
  // Configurar modo de dibujo
  state.btnDraw.addEventListener("change", () => {
    if (state.btnDraw.checked) {
      state.mode = "draw";
      state.btnDraw.classList.add("active");
      state.svg.style.cursor = "crosshair";
    } else {
      state.mode = null;
      state.btnDraw.classList.remove("active");
    }
  });
  // Configurar modo de borrado
  state.btnDelete.addEventListener("change", () => {
    if (state.btnDelete.checked) {
      state.mode = "delete";
      state.btnDelete.classList.add("active");
      state.svg.style.cursor = "pointer";
    } else {
      state.mode = null;
      state.btnDelete.classList.remove("active");
    }
  });
  // Configurar modo mover
  state.btnMove.addEventListener("change", () => {
    if (state.btnMove.checked) {
      state.mode = "move";
      state.btnMove.classList.add("active");
      state.svg.style.cursor = "move";
    } else {
      state.mode = null;
      state.btnMove.classList.remove("active");
    }
  });

  // Inicializar selectores de ubicación
  initLocationSelectors();
}
