#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p data/raw
# Archives are local-only and ignored by Git. Resume partial downloads.
curl -L --fail --retry 2 -C - -o data/raw/foodcom-recipes-and-reviews.zip https://www.kaggle.com/api/v1/datasets/download/irkaal/foodcom-recipes-and-reviews
curl -L --fail --retry 2 -C - -o data/raw/food-101.tar.gz https://data.vision.ee.ethz.ch/cvl/food-101.tar.gz
