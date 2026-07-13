# Notebook ML per l'esame ufficiale

Ogni notebook è autosufficiente e distingue chiaramente ciò che è
caricato dal prodotto da ciò che è un esperimento didattico.

| File | Modello | Stato nel prodotto |
| --- | --- | --- |
| `01_condition_state_mlp.ipynb` | MLP PyTorch su embedding Fashion-CLIP | **In uso** per lo stato del capo |
| `02_wardrobe_gap_mlp.ipynb` | MLP PyTorch multi-label | **In uso** per i gap del guardaroba |
| `03_ghost_risk_logistic_regression.ipynb` | Logistic regression | Esperimento, non collegato alla UI |
| `04_wear_forecast_random_forest.ipynb` | Random forest regression | Esperimento, non collegato alla UI |
| `05_style_clustering_kmeans.ipynb` | K-means | Esperimento, non collegato alla UI |

Fashion-CLIP non compare come training “nostro”: il progetto lo usa
pre-addestrato per inferenza e come estrattore di embedding congelato.
Il recommender outfit, il cost-per-wear, i capi fantasma operativi e le
stime CO₂ sono logiche/regole, non modelli addestrati.

## Esecuzione

Da `backend/`:

```powershell
uv run jupyter nbconvert --to notebook --execute --inplace ../ml/notebooks/exam/*.ipynb
```

I notebook sono consegnati già eseguiti. Rieseguirli serve a dimostrare
riproducibilità; non sovrascrivono i checkpoint usati dall'app.
