import csv
import uuid

# LABELS_PATH = "/mnt/external/floto_labels.csv"
LABELS_PATH = "/Volumes/RPI_LABELS/floto_labels.csv"
LABEL_HEADERS = [
    "labelname",
    "uuid",
    "mac_addr_list",
]

TEST_UUID = "811b56d9-26c7-4cf5-8023-252591ad757"
TEST_UUID2 = "811b56d9-26c7-4cf5-8023-252551ad757"

LABELS_COUNT = 2000


def create_labels_template(filename):
    row_dict = {
        "labelname": None,
        "uuid": None,
        "mac_addr_list": None,
    }

    with open(LABELS_PATH, "w+") as f:
        writer = csv.DictWriter(f, fieldnames=LABEL_HEADERS)
        writer.writeheader()
        for i in range(1, LABELS_COUNT):
            tmp_row = row_dict.copy()
            tmp_row["labelname"] = f"FLOTO_RPI_{i:04d}"
            writer.writerow(tmp_row)


def read_and_update_labels_csv(filename, uuid):
    data = []
    match = {}
    updated = False

    with open(LABELS_PATH, "r") as f:
        reader = csv.DictReader(f, fieldnames=LABEL_HEADERS)
        data.extend(reader)

    for idx, row in enumerate(data):
        if row.get("uuid") == uuid:
            match = row
            print(f"found match at row {idx}")
            return match
    else:
        print(f"match not found, picking first free label")

    # don't assume csv is sorted, pick first free if no match
    for row in data:
        if not row.get("uuid"):
            row["uuid"] = uuid
            match = row
            updated = True
            break

    # write file if we've udpated it
    if updated:
        with open(filename, "w") as f:
            writer = csv.DictWriter(f, fieldnames=LABEL_HEADERS)
            writer.writerows(data)

    return match


def main():
    matched_row2 = read_and_update_labels_csv(LABELS_PATH, TEST_UUID2)
    print(matched_row2)

    matched_row = read_and_update_labels_csv(LABELS_PATH, TEST_UUID)
    print(matched_row)


if __name__ == "__main__":
    main()
