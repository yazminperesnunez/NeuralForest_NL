# Diapositivas · 6 láminas

Reto 1 · Infiltración — Grok Monterrey Build Day, 14 oct 2026. Reto de Pronatura Noreste.
Demo: **https://neuralforest-nl.vercel.app**

---

## 1 · 2022: las presas por debajo del 5 %

- Cerro Prieto y La Boca cayeron a menos del 5 % de su capacidad (según un análisis del Grupo Legislativo PAN en el Congreso de NL, mar 2023).
- La ZMM tenía ~13,500 L/s disponibles contra ~16,500 L/s de consumo regular (misma fuente).
- Al 12 oct 2026, según SADM, las presas principales están al 63.5 % (925.5 millones de m³):
  Cerro Prieto 82.9 %, La Boca 97.9 %, **El Cuchillo 57.6 %**.
- La recuperación no elimina la vulnerabilidad ante la próxima sequía larga.

> Imagen sugerida: foto del vaso seco de Cerro Prieto en 2022.

---

## 2 · La pregunta

**¿Dónde restaurar suelos en las partes altas para que el agua se infiltre
en vez de escurrirse?**

Restaurar es caro y lento. La pregunta no es *si*, sino *dónde primero*.
Hoy esa decisión se toma con recorridos de campo y criterio experto, zona por zona.

---

## 3 · Cómo funciona: datos abiertos + GEE + reglas (listo para Grok)

1. **Google Earth Engine** cruza cinco capas abiertas en las cuencas altas que
   alimentan a las presas: vegetación (NDVI), humedad (NDMI), pendiente, arena
   del suelo e incendios 2015–2025.
2. Divide el terreno arriba de 1,000 m en **celdas de 3 km**, las califica de 0 a 1
   y las clasifica en alta, media y baja por terciles.
3. **Reglas calibradas con los datos reales** proponen un **tipo de obra** por zona
   —barreras de piedra, barreras de material vegetal muerto, zanjas trinchera,
   reforestación o conservar y monitorear— con su justificación y sus salvedades.
   La ficha ya tiene el contrato para que **Grok** redacte la justificación.
4. Todo sale en un mapa estático en 2D y 3D, **ya publicado**.

> Imagen sugerida: el diagrama GEE → zones.geojson → mapa 3D → ficha.

---

## 4 · Resultados

- **563 celdas** de 3 km entre 1,001 y 3,205 m, en 3 cuencas: Cerro Prieto 250,
  Santa Catarina 184, La Boca 129.
- **187 celdas de prioridad alta**. Cerro Prieto concentra **125**; pero el top 25 está
  en el **Santa Catarina (16 de 25)**.
- Las zonas altas tienen la mitad de pendiente (24 % vs 45 %) y menos vegetación
  (NDVI 0.29 vs 0.43) que el promedio: suelo expuesto donde una obra sí es viable.
- **Obras en el top 25:** zanjas 8 · piedra 7 · vegetal muerto 5 · reforestación 5.
- **Robustez:** con 5,000 juegos de pesos al azar, **133 de 187 zonas altas** se
  sostienen; Z001–Z019 en el 100 % de los sorteos.

> Imagen sugerida: captura de la vista 3D con las celdas rojas sobre la sierra.

---

## 5 · Demo

- Vista **3D** de la Sierra Madre con las celdas sobre el relieve real.
- 2D: ranking de zonas, obra sugerida en cada fila y **filtro por obra**.
- Ficha de zona: datos con barra y lectura ("pendiente fuerte", "cobertura muy baja"),
  obra, por qué, alternativas y qué verificar en campo. Flechas para recorrer el ranking.
- Capa de contexto: distritos de riego de Pronatura y presas de abasto.
- **Descargar cartera (CSV)**: las 563 zonas con su obra, lista para llevar a campo.

---

## 6 · Cómo escala

- El script de GEE corre sobre **cualquier cuenca**: se cambia el polígono y los pesos.
- Los datos son abiertos y se actualizan solos: la cartera se puede **recalcular cada año**
  o después de cada incendio grande.
- Para Pronatura y sus aliados: una cartera de obras priorizada y trazable, que
  ordena a dónde mandar la siguiente brigada.
- Siguiente paso: validar en campo las primeras zonas (Z001–Z005), ajustar pesos y
  umbrales con los técnicos de Pronatura y activar Grok para las fichas.

> Cierre: **índice de potencial relativo; no mide volumen infiltrado y requiere
> validación en campo.** Los umbrales de obra son provisionales. Es una herramienta
> para priorizar, no para sustituir al experto.
