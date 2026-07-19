# Asset del guardaroba dimostrativo

Le immagini in `items/` sono copie selezionate dai due dataset già utilizzati
dal progetto. Vengono versionate qui perché `ml/datasets/` è rigenerabile e
ignorata da Git, mentre la demo deve funzionare subito dopo un clone.

- **Fashion-MNIST** — Xiao, Rasul e Vollgraf, *Fashion-MNIST: a Novel Image
  Dataset for Benchmarking Machine Learning Algorithms* (2017). Le silhouette
  sono state ingrandite e ricolorate dallo script
  `backend/scripts/fetch_real_garments.py`.
- **Defect-Clothes v3** — dataset COCO pubblicato su Roboflow Universe dal
  workspace Hawadz, licenza **CC BY 4.0**. La copia originale e i relativi
  README si trovano, quando scaricati, in
  `ml/datasets/Defect-Clothes.v3i.coco/`.

Il profilo quantitativo del seed è ispirato alle righe `balanced` e `minimal`
di `ml/datasets/wardrobe/wardrobe_dataset.csv`: è deliberatamente compatto e
mantiene alcuni segnali utili da mostrare, tra cui due capi fantasma, un capo
danneggiato, una riparazione, una donazione e almeno un gap del guardaroba.
