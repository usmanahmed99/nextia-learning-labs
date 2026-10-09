# Dataset card: Fashion-MNIST

Used by: C06-M09-L01 (case study *Classify clothing images*), `classify-clothing-images.ipynb` and `classify-clothing-images-solution.ipynb`

| Field | Value |
|---|---|
| Source | https://github.com/zalandoresearch/fashion-mnist (files in `data/fashion/`; also at http://fashion-mnist.s3-website.eu-central-1.amazonaws.com/) |
| Publisher / creator | Zalando Research (Han Xiao, Kashif Rasul, Roland Vollgraf). Paper: "Fashion-MNIST: a Novel Image Dataset for Benchmarking Machine Learning Algorithms", arXiv:1708.07747, 2017 |
| Licence | MIT License, Copyright © 2017 Zalando SE — https://github.com/zalandoresearch/fashion-mnist/blob/master/LICENSE |
| Attribution text | Fashion-MNIST by Zalando Research (Xiao, Rasul and Vollgraf, 2017), https://github.com/zalandoresearch/fashion-mnist, MIT License, Copyright © 2017 Zalando SE. |
| Version or access date | Repository `master`, downloaded 2026-10-08; the SHA-256 values below fix the exact bytes (MD5 values match the repository README) |
| File used | The four original gzip files. Kept in `data/`: no. The notebook downloads them from the source and checks them; MIT allows redistribution, but the files are 31 MB |
| SHA-256 | `train-images-idx3-ubyte.gz` 3aede38d61863908ad78613f6a32ed271626dd12800ba2636569512369268a84 · `train-labels-idx1-ubyte.gz` a04f17134ac03560a47e3764e11b92fc97de4d1bfaf8ba1a3aa29af54cc90845 · `t10k-images-idx3-ubyte.gz` 346e55b948d973a97e58d2351dde16a484bd415d4595297633bb08f03db6a073 · `t10k-labels-idx1-ubyte.gz` 67da17c76eaffca5446c3361aaab5c3cd6d1c2608764d35dfb1850b086bf8dd5 |
| Size | 60,000 training and 10,000 test images, each 28 × 28 grey pixels (784 values from 0 to 255) with one label from 10 classes; 30.9 MB compressed |

## What one row means

One image is one product photo from Zalando's online catalogue, shrunk to 28 × 28 pixels in grey. The target is its category: 0 T-shirt/top, 1 Trouser, 2 Pullover, 3 Dress, 4 Coat, 5 Sandal, 6 Shirt, 7 Sneaker, 8 Bag, 9 Ankle boot. Each class has 6,000 training and 1,000 test images.

## Why this dataset

It is real image data with a clear permissive licence, it is small enough to train on a CPU, and it shows every idea the case study needs: pixels as features, a logistic-regression baseline that a convolutional network beats, confusions that a person understands (shirt, T-shirt/top, pullover, coat), and an augmentation that keeps the label true (a left-right flip). MNIST digits were compared: the original page had no licence statement and no files on 2026-10-08, and the task is too easy. KMNIST was compared: its licence is CC BY-SA 4.0 (share-alike), which is not on the course's list. Details: `reference/c06/m09/l01/DATASET-RESEARCH.md` in the course repository.

## Changes we made

None to the files. The notebook reads them with NumPy, divides the pixels by 255, and uses a fixed, stratified sample to keep training short on a CPU: 10,000 training images and 5,000 validation images, both from the training file (`train_test_split`, `random_state=0`). The 10,000 test images are used once, at the end.

## Limitations and cautions

- The images are tiny (28 × 28), grey, centred, on a black background, one product per image. Real shop photos are larger, in colour, and vary in background, angle and light, so a model trained here will not work on them without new training and testing.
- The products come from one European retailer's catalogue around 2017; styles, cultures and price ranges outside it are under-represented.
- Some labels are hard or arguably wrong even for a person (shirt vs T-shirt/top vs pullover), so accuracy has a ceiling below 100%.
- The images show products, not people; nothing in them is about a customer.
