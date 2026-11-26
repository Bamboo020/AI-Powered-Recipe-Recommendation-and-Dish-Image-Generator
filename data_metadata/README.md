# Real data and provenance

Actual downloaded and counted records:

| Dataset | Local files | Count / usage |
| --- | --- | --- |
| Food.com, Kaggle irkaal version 2 | `data/raw/foodcom/recipes.csv` | 522,517 recipes |
| Same source | `data/raw/foodcom/reviews.csv` | 1,401,982 reviews; not used by current ranking |
| Prepared starter | `data/processed/foodcom_starter.jsonl` | First 5,000 valid short recipes; not random |
| Photo category extension | `data/processed/foodcom_photo_extension.jsonl` | 106 additional unique recipes to expand five-category coverage; source IDs pinned in photo_extension_ids.json |
| Official Food-101 archive | `data/raw/food-101.tar.gz` | Complete 101-class / 101,000-image archive |
| Extracted supported classes | `data/raw/food101/food-101/images/` | 5 classes × 1,000 images; only these classes extracted |
| Image split manifests | `data/processed/food101/{train,validation,test}.jsonl` | 3,000 / 750 / 1,250 images, disjoint |

The app contains **5,106 real recipes + 6 labeled illustrative fixtures**. Real records preserve source dataset ID, original title/steps, textual quantities and ingredient names (`source_name`). Source URLs are constructed from IDs, not individually live-verified. Ingredient aliases are limited; source `rice` stays `rice_unspecified` rather than being assumed raw or cooked. Units and cuisine are not invented. Starter records have positive known time <=120 minutes and <=15 ingredients; photo extension allows <=25 ingredients. These selection rules introduce coverage bias.

## Sources and terms

- Food.com publisher: https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews . Kaggle API metadata declares CC0: Public Domain, current version 2. This publisher declaration is not an independent verification of upstream recipe/image rights. Raw records and review authors are kept local, not uploaded to GitHub.
- Food-101 official source: https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/ . Images originate from Foodspotting contributors; the source notice limits use beyond scientific fair use unless negotiated with image owners. Public download does not imply unrestricted redistribution. Hugging Face card: https://huggingface.co/datasets/ethz/food101 . Only metadata/scripts/results are committed.
- `datasets.json` stores actual counts, archive SHA256, extraction policy and provenance.

**Version distinction:** `irkaal/foodcom-recipes-and-reviews` uses `RecipeId`, ISO-8601 `TotalTime`, and R-style list columns in `recipes.csv`. `RAW_recipes.csv` / `RAW_interactions.csv` belong to another Food.com dataset version. The preparation script targets the downloaded irkaal schema, not the other one.

## Reproduction

Run `scripts/download_data.sh`, `prepare_foodcom.py`, `import_foodcom.py`, `extend_photo_recipes.py` and import its output. For CNN run `prepare_food101.py` then `train_cnn.py`. See repository README for exact commands. Real data lives in ignored `data/`; it is not automatically imported by server startup. Existing six fixtures are separate records with `demo-` IDs and explicit provenance.

`demo_recipes.json` remains project-authored AI-assisted illustrative material, not verified Chinese recipe data. No images from Food-101 are assumed to correspond to individual Food.com records. Photo-to-recipe mapping is a documented heuristic requiring category confirmation, and still needs human relevance evaluation.

`boston_food_resources.json` is the validated, human-reviewed starter registry for recurring free-food programs. Each entry must use a declared HTTPS source, a unique ID, an explicit review date and a valid recurring schedule. Editing this file expands or corrects the reviewed directory without changing Python source; runtime source checks still do not establish live stock or holiday availability.
