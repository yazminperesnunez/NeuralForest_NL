# Guion del pitch · 3 minutos

Tiempos: 30 s problema · 90 s demo · 30 s método y límites · 30 s escala.
Demo en vivo: **https://neuralforest-nl.vercel.app** (abre directo en 3D).
Tener el video de respaldo abierto en otra pestaña por si falla la red.

---

## 0:00 – 0:30 · El problema

> Según un análisis del Grupo Legislativo PAN en el Congreso, en 2022 Cerro
> Prieto y La Boca bajaron a menos del cinco por ciento. Monterrey tenía trece
> mil quinientos litros por segundo disponibles contra dieciséis mil quinientos
> de consumo. Hoy, según SADM, las presas están al sesenta y tres por ciento,
> y El Cuchillo apenas pasa la mitad. La recuperación no quita el problema: la
> próxima sequía larga nos vuelve a encontrar igual.
>
> El agua de esas presas nace arriba, en la sierra. Si el suelo de las partes
> altas está desnudo o quemado, el agua escurre en vez de infiltrarse.
> Restaurar ese suelo sirve, pero es caro: la pregunta de Pronatura no es si
> restaurar, es **dónde empezar**.

## 0:30 – 2:00 · Demo

*(Abre la página: vista 3D de la Sierra Madre.)*

> Esto es la Sierra Madre Oriental, en relieve real. Encima están las cuencas
> altas de Santa Catarina, La Boca y Cerro Prieto: **563 celdas de tres
> kilómetros, todas arriba de mil metros**. Rojo es prioridad alta: **187 celdas**.
>
> Dos cosas saltan a la vista. La cuenca de **Cerro Prieto concentra 125 de las
> 187 celdas altas**. Pero las más críticas del ranking están en la cuenca alta
> del **Santa Catarina: 16 de las primeras 25**.

*(Clic en "Ver en 2D" y luego en Z001.)*

> Entro a la zona número uno. Pendiente de 32 %, vegetación muy baja —NDVI de
> 0.21—, a 1,455 metros. Cada dato trae su barra y su lectura: "fuerte",
> "cobertura muy baja". Y la obra sugerida: **barreras de piedra acomodada**,
> porque con esa pendiente se necesita una obra firme contra el escurrimiento.
> Trae alternativas y, muy importante, lo que hay que verificar en campo:
> material, cárcavas, acceso, tenencia de la tierra y ganado.

*(Flecha → dos veces: Z002, Z003.)*

> Con las flechas recorro el ranking. La zona dos pide zanjas trinchera, la tres
> barreras de material vegetal muerto: **en las 25 primeras salen las cuatro
> obras de restauración**, no una receta única.

*(Filtro "Obra: zanjas trinchera", luego "todas". Prender distritos de riego.)*

> Puedo filtrar por tipo de obra para planear una brigada. Y como contexto, los
> distritos de riego que nos pasó Pronatura: aguas abajo está quien usa el agua
> que no se infiltró arriba.

*(Clic en Descargar cartera.)*

> Y esto es lo que se llevan a campo: la cartera completa en CSV, las 563 zonas
> con su obra sugerida y su justificación.

## 2:00 – 2:30 · Método y límites

> Atrás hay un script de Google Earth Engine que cruza cinco capas abiertas:
> vegetación y humedad de Sentinel-2, pendiente de SRTM, arena de OpenLandMap e
> incendios de MODIS. Probamos los pesos con **5,000 combinaciones al azar**:
> **133 de las 187 zonas altas siguen altas con casi cualquier ponderación**, y
> las primeras 19 lo son en el 100 % de los sorteos.
>
> Y hay que decirlo claro: **esto es un índice de potencial relativo. No mide
> cuánta agua se infiltra y no sustituye la visita de campo.** Las obras de hoy
> salen de **reglas calibradas con los datos reales**; los pesos y los umbrales
> son una primera propuesta que tiene que validar Pronatura.

## 2:30 – 3:00 · Escala

> El mismo script corre en cualquier cuenca: se cambia el polígono y listo.
> Los datos son abiertos, así que la cartera se puede recalcular cada año o
> después de cada incendio grande. Y la ficha de cada zona ya tiene el contrato
> para que **Grok** redacte la justificación con los mismos datos y la misma
> lista cerrada de obras.
>
> Lo que entregamos no es un mapa bonito: es una forma repetible de decidir a
> dónde mandar la siguiente brigada. Y ya está publicada.

---

## Cifras clave (para tener a la mano)

| Dato | Valor |
|---|---|
| Celdas analizadas | 563 de 3 km, arriba de 1,000 m (1,001 a 3,205 m) |
| Por cuenca | Cerro Prieto 250 · Santa Catarina 184 · La Boca 129 |
| Prioridad alta | 187 (Cerro Prieto 125 · Santa Catarina 47 · La Boca 15) |
| Top 25 por cuenca | Santa Catarina 16 · Cerro Prieto 8 · La Boca 1 |
| Zonas altas vs. todas | NDVI promedio 0.29 vs 0.43 · pendiente 24 % vs 45 % |
| Top 5 | Z001, Z002, Z003, Z005 (Santa Catarina) · Z004 (Cerro Prieto), índice 0.68–0.70 |
| Obras en el top 25 | zanjas 8 · piedra 7 · vegetal muerto 5 · reforestación 5 |
| Obras en las 187 altas | reforestación 70 · piedra 67 · vegetal muerto 33 · zanjas 17 |
| Robustez de pesos | 133 de 187 altas robustas · Z001–Z019 al 100 % · ρ = 0.993 |
| Presas (SADM, 12 oct 2026) | total 63.5 % · Cerro Prieto 82.9 % · La Boca 97.9 % · El Cuchillo 57.6 % |

## Preguntas probables

- **¿Por qué celdas de 3 km?** Es el tamaño que corre en minutos en GEE para toda
  la zona. El script lo controla con una variable: se baja a 1 km para una cuenca sola.
- **¿Por qué esos pesos?** Son una primera propuesta del equipo y están en una
  variable arriba del script. La prueba de 5,000 sorteos muestra que el resultado
  no depende de ellos: 133 de las 187 zonas altas se sostienen.
- **¿Dónde está la IA?** Las obras de hoy salen de reglas calibradas con los datos,
  para que el demo sea trazable y no dependa de la red. La ficha ya tiene el contrato
  para que Grok redacte la justificación; si su respuesta no cumple el contrato,
  cae a reglas y se marca.
- **¿Por qué Z003 dice "relativamente arenoso" y no lleva zanja?** Las reglas revisan
  primero la pendiente: con 20.7 % toca una obra transversal ligera (barreras de
  material vegetal muerto). La zanja es para pendientes suaves.
- **¿Por qué la cuenca de Cerro Prieto tiene tantas zonas altas?** Tiene más celdas
  (250) y más terreno con vegetación baja; aun así, las zonas más críticas del ranking
  están en el Santa Catarina.
- **¿Sirve sin internet?** Sí: las recomendaciones se pre-generan y el mapa es estático.
