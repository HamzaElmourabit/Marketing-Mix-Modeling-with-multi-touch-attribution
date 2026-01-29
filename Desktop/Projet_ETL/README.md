# ETL Data Extraction Interface

Ce dépôt contient un notebook d'extraction et une application Gradio de démonstration.

Déployer sur Hugging Face Spaces (résumé):

1. Créez un repo Space (Python) sur https://huggingface.co/spaces
2. Poussez ce dépôt (ou copiez `app.py` + `requirements.txt`) dans le repo Space
3. Le Space démarrera automatiquement et exposera l'interface publique

Exécuter localement:

```bash
pip install -r requirements.txt
python app.py
```

L'interface sera accessible sur `http://localhost:7860`.

Remarque: L'application `app.py` ici propose une démo OCR locale. Pour intégrer la logique complète (Tensorlake, extraction structurée), fournissez la clé API et j'intègrerai l'appel dans `app.py`.
