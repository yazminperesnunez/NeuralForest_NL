# Diapositivas · 5 láminas

Reto 1 · Infiltración — Grok Monterrey Build Day, 14 oct 2026. Reto de Pronatura Noreste.

---

## 1 · 2022: las presas por debajo del 5 %

- Cerro Prieto y La Boca cayeron a menos del 5 % de su capacidad.
- La ZMM tenía ~13,500 L/s disponibles contra ~16,500 L/s de consumo regular.
- Al 12 oct 2026 las presas principales están al 63.5 % (925.5 millones de m³):
  la recuperación no elimina la vulnerabilidad ante la próxima sequía larga.

> Imagen sugerida: foto del vaso seco de Cerro Prieto en 2022.

---

## 2 · La pregunta

**¿Dónde restaurar suelos en las partes altas para que el agua se infiltre
en vez de escurrirse?**

Restaurar es caro y lento. La pregunta no es *si*, sino *dónde primero*.
Hoy esa decisión se toma con recorridos de campo y criterio experto, zona por zona.

---

## 3 · Cómo funciona: datos abiertos + GEE + IA

1. **Google Earth Engine** cruza cinco capas abiertas en las cuencas altas que
   alimentan a las presas: vegetación (NDVI), humedad (NDMI), pendiente, arena
   del suelo e incendios de los últimos 10 años.
2. Divide el terreno arriba de 1000 m en **celdas de 3 km**, las califica de 0 a 1
   y las clasifica en alta, media y baja por terciles.
3. **Grok** toma los atributos de cada zona y propone un **tipo de obra**
   —barreras de piedra, barreras de material vegetal muerto, zanjas trinchera,
   reforestación o conservar y monitorear— con su justificación y sus salvedades.
4. Todo sale en un mapa estático, sin infraestructura: se puede publicar hoy.

> Imagen sugerida: el diagrama GEE → zones.geojson → mapa → ficha.

---

## 4 · Demo

- Mapa con las zonas prioritarias sobre relieve; filtros por prioridad.
- Clic en una zona: atributos + obra recomendada + por qué + salvedades.
- Capa de contexto: distritos de riego de Pronatura y presas de abasto.
- **Descargar cartera (CSV)**: la lista de zonas con su obra, lista para llevarla a campo.
- Metodología y fuentes abiertas en una página aparte.

---

## 5 · Cómo escala

- El script de GEE corre sobre **cualquier cuenca**: se cambia el polígono y los pesos.
- Los datos son abiertos y se actualizan solos: la cartera se puede **recalcular cada año**
  o después de cada incendio grande.
- Para Pronatura y sus aliados: una cartera de obras priorizada y trazable, que
  ordena a dónde mandar la siguiente brigada.
- Siguiente paso: validar en campo las primeras zonas y ajustar pesos y umbrales
  con los técnicos de Pronatura.

> Cierre: **índice de potencial relativo; no mide volumen infiltrado y requiere
> validación en campo.** Es una herramienta para priorizar, no para sustituir al experto.
