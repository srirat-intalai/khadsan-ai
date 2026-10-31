| การทดลอง | เริ่มจาก | Optimizer | LR | Batch | Weight decay | Epoch | Val mAP50 | Test Precision | Test Recall | Test F1 | Test mAP50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4_rmsprop | pretrained | RMSProp | 0.001 fixed | 16 | 0.0005 | 32 | 0.3175 | 0.3069 | 0.4424 | 0.3624 | 0.2911 |
| 5_cosine_lr | pretrained | SGD | 0.01 cosine | 16 | 0.0005 | 60 | 0.975 | 0.9413 | 0.9643 | 0.9527 | 0.9698 |
| 8_cosine_more_data | pretrained | SGD | 0.01 cosine | 16 | 0.0005 | 60 | 0.973 | 0.9459 | 0.9417 | 0.9438 | 0.969 |
| 9_rmsprop_low_lr | pretrained | RMSProp | 0.0001 fixed | 16 | 0.0005 | 38 | 0.6728 | 0.5633 | 0.669 | 0.6116 | 0.6657 |
