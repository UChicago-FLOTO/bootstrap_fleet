# Usage

Reads from a USB drive, which must have a file named `floto_labels.csv` file on the root path, with the following format:

```
labelname,uuid,mac_addr_list
FLOTO_RPI_0001,e7bcc58048c42bfbbd42b7c85a7ac479,D8:3A:DD:02:E7:75 CE:93:37:DF:93:A3
FLOTO_RPI_0002,3ab03aa2bfeaae843a1102e62abdd5b5,D8:3A:DD:0C:A3:C1 76:71:66:22:52:C4
FLOTO_RPI_0003,0f76d2c37b0d10ebd557b93f67af66b0,D8:3A:DD:0C:A5:5F 02:6B:B3:B5:7C:43
FLOTO_RPI_0004,661ac23525ea6a1a525bc803ad386d25,D8:3A:DD:0C:A4:7B BE:C5:37:7A:F2:E6
FLOTO_RPI_0005,b5c67713935dc487225c4f3fc9fd2508,D8:3A:DD:0C:A4:F6 C2:19:F4:69:FF:8D
FLOTO_RPI_0006,,
FLOTO_RPI_0007,,
FLOTO_RPI_0008,,
```

On boot, the application will read this file from the usb drive and search for its UUID in the list.
If not found, it will pick the first "free" label, and update it with its UUID and mac addresses.
