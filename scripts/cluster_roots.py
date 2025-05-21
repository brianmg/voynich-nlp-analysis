import os
import re
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import json
import argparse
import umap
from typing import Union
import pacmap

# === CONFIGURATION ===
def get_reducer(reducer: str) -> Union[PCA, umap.UMAP, pacmap.PaCMAP]:
    """
    Returns PCA, UMAP, or PaCMAP reducer based on argument.
    """
    if reducer == "umap":
        return umap.UMAP()
    elif reducer == "pacmap":
        return pacmap.PaCMAP(
            n_components=2,
            n_neighbors=5,
            MN_ratio=0.3,
            FP_ratio=1.5,
            random_state=42
        )
    else:
        return PCA(n_components=2)

parser = argparse.ArgumentParser()
parser.add_argument("--reducer", type=str, help="Reducer to use: 'pca', 'umap', or 'pacmap'.", default="pca")
args = parser.parse_args()
directory = './data/voynitchese'  # path to your Voynich text files
suffixes = ['aiin', 'dy', 'in', 'chy', 'chey', 'edy', 'ey', 'y']
# === STRIP SUFFIX FUNCTION ===
def strip_suffix(word):
    for suffix in sorted(suffixes, key=len, reverse=True):
        if word.endswith(suffix):
            return re.sub(f'{suffix}$', '', word)
    return word

# === LOAD AND CLEAN DATA ===
voynich_words = []
for filename in os.listdir(directory):
    filepath = os.path.join(directory, filename)
    if os.path.isfile(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            words = f.read().split()
            voynich_words.extend(words)

# === STRIP SUFFIXES ===
stripped_words = [strip_suffix(word) for word in voynich_words]
unique_stripped_words = sorted(set(stripped_words))

# === EMBED WITH SBERT ===
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
embeddings = model.encode(
    unique_stripped_words,
    normalize_embeddings=True,
    convert_to_numpy=True,
    show_progress_bar=False
)

# === CLUSTER WITH KMEANS ===
kmeans = KMeans(n_clusters=10, n_init=10, random_state=42).fit(embeddings)
labels = kmeans.labels_

print(f"🔍 Unique stripped words: {len(unique_stripped_words)}")
# === DIMENSIONALITY REDUCTION (UMAP or PCA) ===
print(f"⏬ Using reducer: {args.reducer} on {len(embeddings)} points")
reducer = get_reducer(args.reducer)
try:
    reduced = reducer.fit_transform(embeddings)
except ValueError as e:
    print(f"⚠️ PaCMAP failed with error: {e}")
    print("🔁 Falling back to PCA for visualization.")
    reducer = PCA(n_components=2)
    reduced = reducer.fit_transform(embeddings)

# === PLOT CLUSTERS ===
plt.figure(figsize=(12, 8))
plt.scatter(reduced[:, 0], reduced[:, 1], c=labels, cmap='tab10')
plt.title("Voynich Clusters After Suffix Stripping")
plt.xlabel("Component 1")
plt.ylabel("Component 2")
plt.grid(True)
plt.show()

# === DISPLAY TOP WORDS PER CLUSTER ===
clustered_words = {i: [] for i in range(10)}
for word, label in zip(unique_stripped_words, labels):
    clustered_words[label].append(word)

for i in range(10):
    print(f"\nCluster {i}: {clustered_words[i][:10]}")

# === EXPORT UNIQUE STRIPPED WORDS TO JSON ===
with open("./data/unique_stripped_words.json", "w") as f:
    json.dump(unique_stripped_words, f)
print("✅ Saved unique stripped words to unique_stripped_words.json")


# === EXPORT STRIPPED WORD → CLUSTER MAPPING TO JSON ===
cluster_lookup = {word: int(label) for word, label in zip(unique_stripped_words, labels)}

with open("./data/stripped_cluster_lookup.json", "w") as f:
    json.dump(cluster_lookup, f)

print("✅ Saved stripped word → cluster mapping to stripped_cluster_lookup.json")
