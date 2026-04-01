import torch
import random
import os
from transformers import BertTokenizer, BertForSequenceClassification
import torch.optim as optim

# =========================
# CONFIG
# =========================
MODEL_PATH = "bert-base-uncased"   # or your trained model
SAVE_PATH = "rank_model/pytorch_model.bin"
BATCH_SIZE = 16
EPOCHS = 5
LR = 2e-5

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =========================
# LOAD MODEL
# =========================
tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
model = BertForSequenceClassification.from_pretrained(MODEL_PATH, num_labels=1)
model = model.to(device)

optimizer = optim.Adam(model.parameters(), lr=LR)

# =========================
# DATA FORMAT
# =========================
# lines = [
#   (query, positive_doc, negative_doc),
#   ...
# ]

def load_data(path):
    """
    Expecting file format:
    query \t positive_doc \t negative_doc
    """
    lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            q, pos, neg = line.strip().split("\t")
            lines.append((q, pos, neg))
    return lines

# =========================
# TRAINING FUNCTION
# =========================
def train(lines):
    model.train()

    for epoch in range(EPOCHS):
        random.shuffle(lines)

        total_loss = 0

        for i in range(0, len(lines), BATCH_SIZE):
            batch = lines[i:i+BATCH_SIZE]

            queries, pos_docs, neg_docs = zip(*batch)

            # truncate for safety
            queries = [q[:200] for q in queries]
            pos_docs = [d[:200] for d in pos_docs]
            neg_docs = [d[:200] for d in neg_docs]

            # ---- tokenize positive pairs ----
            pos_inputs = tokenizer(
                list(queries),
                list(pos_docs),
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )

            # ---- tokenize negative pairs ----
            neg_inputs = tokenizer(
                list(queries),
                list(neg_docs),
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )

            # move to GPU
            pos_inputs = {k: v.to(device) for k, v in pos_inputs.items()}
            neg_inputs = {k: v.to(device) for k, v in neg_inputs.items()}

            # ---- forward ----
            pos_scores = model(**pos_inputs).logits.squeeze()
            neg_scores = model(**neg_inputs).logits.squeeze()

            # ---- pairwise ranking loss ----
            loss = -torch.log(torch.sigmoid(pos_scores - neg_scores)).mean()

            # ---- backward ----
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

            total_loss += loss.item()

            if i % (BATCH_SIZE * 10) == 0:
                print(f"Epoch {epoch} Step {i} Loss: {loss.item():.4f}")

        print(f"Epoch {epoch} Avg Loss: {total_loss:.4f}")

        # save checkpoint
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        torch.save(model.state_dict(), SAVE_PATH)

# =========================
# INFERENCE (RERANK)
# =========================
def rerank(query, docs):
    model.eval()

    queries = [query] * len(docs)
    docs = [d[:200] for d in docs]

    inputs = tokenizer(
        queries,
        docs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        scores = model(**inputs).logits.squeeze()

    scores = scores.cpu().numpy().tolist()

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in ranked]


# =========================
# RUN TRAINING
# =========================
if __name__ == "__main__":
    train_data = load_data("train_data.txt")
    train(train_data)

    # Example test
    test_query = "Apple stock news"
    test_docs = [
        "Apple releases new iPhone",
        "Tesla stock falls sharply",
        "Microsoft earnings increase"
    ]

    ranked = rerank(test_query, test_docs)

    print("\nTop Results:")
    for r in ranked:
        print("-", r)