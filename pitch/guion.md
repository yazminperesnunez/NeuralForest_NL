# Guion del pitch · 3 minutos

Tiempos: 30 s problema · 90 s demo · 30 s método y límites · 30 s escala.
Tener el video de respaldo abierto en otra pestaña por si falla la red.

---

## 0:00 – 0:30 · El problema

> En 2022 Cerro Prieto y La Boca bajaron a menos del cinco por ciento.
> Monterrey tenía trece mil quinientos litros por segundo disponibles contra
> dieciséis mil quinientos de consumo. Hoy las presas están al sesenta y tres
> por ciento, pero eso no quita el problema: la próxima sequía larga nos vuelve
> a encontrar igual.
>
> El agua de esas presas nace arriba, en la sierra. Si el suelo de las partes
> altas está desnudo o quemado, el agua escurre en vez de infiltrarse.
> Restaurar ese suelo sirve, pero es caro: la pregunta de Pronatura no es si
> restaurar, es **dónde empezar**.

## 0:30 – 2:00 · Demo

*(Mapa en pantalla, zonas ya cargadas.)*

> Esto son las cuencas altas que alimentan a La Boca, Cerro Prieto y El Cuchillo.
> Cada cuadro es una celda de tres kilómetros, calificada por su potencial de
> infiltración: rojo es prioridad alta.

*(Clic en la zona 1.)*

> Entro a la zona más prioritaria. Aquí están sus datos: pendiente, vegetación,
> años con incendio, arena del suelo, elevación. Y esta es la parte nueva:
> **Grok lee esos atributos y propone el tipo de obra** —en este caso barreras
> de piedra acomodada—, explica por qué con los números de la zona, da
> alternativas y, muy importante, dice sus salvedades: que hace falta piedra en
> sitio y que sin control de ganado la vegetación no se recupera.

*(Prender la capa de distritos de riego.)*

> Como contexto, los distritos de riego que nos pasó Pronatura: aguas abajo,
> es quien usa el agua que no se infiltró arriba. Y las presas de abasto.

*(Clic en Descargar cartera.)*

> Y esto es lo que se llevan a campo: la cartera completa en CSV, zona por zona,
> con su obra sugerida y su justificación.

## 2:00 – 2:30 · Método y límites

> Atrás hay un script de Google Earth Engine que cruza cinco capas abiertas:
> vegetación y humedad de Sentinel-2, pendiente de SRTM, arena de OpenLandMap e
> incendios de MODIS. Todo está documentado en la página de metodología, con los
> pesos y las fuentes.
>
> Y hay que decirlo claro: **esto es un índice de potencial relativo. No mide
> cuánta agua se infiltra y no sustituye la visita de campo.** Los pesos y los
> umbrales de obra son una primera propuesta que tiene que validar Pronatura.

## 2:30 – 3:00 · Escala

> El mismo script corre en cualquier cuenca: se cambia el polígono y listo.
> Los datos son abiertos, así que la cartera se puede recalcular cada año o
> después de cada incendio grande.
>
> Lo que entregamos no es un mapa bonito: es una forma repetible de decidir a
> dónde mandar la siguiente brigada.

---

## Preguntas probables

- **¿Por qué celdas de 3 km?** Es el tamaño que corre en minutos en GEE para toda
  la zona. El script lo controla con una variable: se baja a 1 km para una cuenca sola.
- **¿Por qué esos pesos?** Son una primera propuesta del equipo; están en una
  variable arriba del script justo para que un especialista los mueva.
- **¿Grok inventa datos?** El prompt le prohíbe usar nada fuera de los atributos
  de la zona y le fija la lista de obras permitidas. La respuesta se valida contra
  ese contrato; si falla dos veces, cae a una recomendación por reglas y se marca.
- **¿Sirve sin internet?** Sí: las recomendaciones se pre-generan y el mapa es estático.
