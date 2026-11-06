# Protocol Format Specification

RoboLab protocols are JSON files structured as follows:

```json
{
  "name": "Example Protocol",
  "description": "Standard 2-Plate Media Change",
  "target_head": "machine_1_8x1000",
  "steps": [
    {
      "action": "Pick Up Tip",
      "slot": "Slot_4",
      "well": "A1",
      "volume": 0.0,
      "eight_ch_symmetric": true,
      "mounted_channels": "A-H",
      "label": "Pick up 8 tips"
    },
    {
      "action": "Aspirate Media",
      "slot": "Slot_3",
      "well": "A1",
      "volume": 500.0,
      "eight_ch_symmetric": true,
      "mounted_channels": "A-H",
      "label": "Aspirate 500 uL old media"
    }
  ]
}
```
