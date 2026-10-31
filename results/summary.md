| การทดลอง | เริ่มจาก | Optimizer | LR | Batch | Weight decay | Epoch | Val mAP50 | Test Precision | Test Recall | Test F1 | Test mAP50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1_scratch_sgd | scratch | SGD | 0.01 fixed | 16 | 0.0005 | 54 | 0.946 | 0.8912 | 0.8931 | 0.8921 | 0.9421 |
| 2_pretrained_sgd | pretrained | SGD | 0.01 fixed | 16 | 0.0005 | 46 | 0.9597 | 0.9036 | 0.9113 | 0.9074 | 0.9516 |
| 3_adam | pretrained | Adam | 0.001 fixed | 16 | 0.0005 | 60 | 0.967 | 0.9143 | 0.9183 | 0.9163 | 0.9516 |
| 4_rmsprop | pretrained | RMSProp | 0.001 fixed | 16 | 0.0005 | 32 | 0.3175 | 0.3069 | 0.4424 | 0.3624 | 0.2911 |
| 5_cosine_lr | pretrained | SGD | 0.01 cosine | 16 | 0.0005 | 60 | 0.975 | 0.9413 | 0.9643 | 0.9527 | 0.9698 |
| 6_batch32 | pretrained | SGD | 0.01 fixed | 32 | 0.0005 | 59 | 0.96 | 0.9231 | 0.9285 | 0.9258 | 0.9624 |
| 7_no_weight_decay | pretrained | SGD | 0.01 fixed | 16 | 0.0 | 53 | 0.965 | 0.9052 | 0.9299 | 0.9174 | 0.9532 |
