| การทดลอง | เริ่มจาก | Optimizer | LR | Batch | Weight decay | Epoch | Val mAP50 | Test Precision | Test Recall | Test F1 | Test mAP50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1_scratch_sgd | scratch | SGD | 0.01 fixed | 16 | 0.0005 | 49 | 0.9387 | 0.8821 | 0.8545 | 0.8681 | 0.9253 |
| 2_pretrained_sgd | pretrained | SGD | 0.01 fixed | 16 | 0.0005 | 56 | 0.9696 | 0.8971 | 0.9196 | 0.9082 | 0.9488 |
| 3_adam | pretrained | Adam | 0.001 fixed | 16 | 0.0005 | 41 | 0.9735 | 0.8941 | 0.938 | 0.9155 | 0.9538 |
| 4_rmsprop | pretrained | RMSProp | 0.001 fixed | 16 | 0.0005 | 42 | 0.5179 | 0.3588 | 0.623 | 0.4553 | 0.472 |
| 5_cosine_lr | pretrained | SGD | 0.01 cosine | 16 | 0.0005 | 60 | 0.9751 | 0.9274 | 0.9599 | 0.9434 | 0.9595 |
| 6_batch32 | pretrained | SGD | 0.01 fixed | 32 | 0.0005 | 59 | 0.9721 | 0.8952 | 0.918 | 0.9065 | 0.9448 |
| 7_no_weight_decay | pretrained | SGD | 0.01 fixed | 16 | 0.0 | 37 | 0.9679 | 0.8789 | 0.916 | 0.8971 | 0.9317 |
