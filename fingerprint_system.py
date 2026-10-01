from database import get_connection


class FingerprintSystem:

    def __init__(self):
        self.database = "attendance.db"

    def check_device(self):
        """
        Check whether a fingerprint device is available.

        The current AttendX laptop may not have a fingerprint
        sensor, so this function safely reports that status.
        """

        try:
            import subprocess

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-PnpDevice | Where-Object { "
                    "$_.FriendlyName -match 'fingerprint|biometric' "
                    "} | Select-Object -ExpandProperty FriendlyName"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            devices = []

            for line in result.stdout.splitlines():
                line = line.strip()

                if line:
                    devices.append(line)

            return devices

        except Exception:
            return []


    def device_available(self):
        devices = self.check_device()

        return len(devices) > 0


    def get_device_status(self):

        devices = self.check_device()

        if not devices:
            return {
                "available": False,
                "devices": []
            }

        return {
            "available": True,
            "devices": devices
        }


    def register_fingerprint(self, student_id):

        if not self.device_available():
            return False, (
                "No fingerprint device detected.\n\n"
                "Please connect a supported fingerprint "
                "device before registering."
            )

        return False, (
            "Fingerprint registration is ready for the "
            "fingerprint hardware integration."
        )


    def verify_fingerprint(self, student_id):

        if not self.device_available():
            return False, (
                "No fingerprint device detected.\n\n"
                "Fingerprint verification cannot be performed "
                "on this laptop."
            )

        return False, (
            "Fingerprint verification is ready for the "
            "fingerprint hardware integration."
        )


    def save_fingerprint_record(self, student_id, fingerprint_data):

        try:
            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    fingerprint_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                INSERT INTO fingerprints
                (
                    student_id,
                    fingerprint_data
                )
                VALUES (?, ?)
                """,
                (
                    student_id,
                    fingerprint_data
                )
            )

            connection.commit()
            connection.close()

            return True

        except Exception:
            return False


def check_fingerprint_device():

    system = FingerprintSystem()

    status = system.get_device_status()

    if status["available"]:
        print("Fingerprint device detected.")

        for device in status["devices"]:
            print("-", device)

    else:
        print("No fingerprint device detected.")


if __name__ == "__main__":

    print("=" * 45)
    print("        ATTENDX FINGERPRINT SYSTEM")
    print("=" * 45)

    system = FingerprintSystem()

    status = system.get_device_status()

    if status["available"]:

        print()
        print("Fingerprint device detected:")
        print()

        for device in status["devices"]:
            print("-", device)

        print()
        print("Fingerprint hardware is ready for integration.")

    else:

        print()
        print("No fingerprint device detected.")
        print()
        print(
            "This laptop does not currently have a "
            "supported fingerprint sensor."
        )

    print()
    print("Database: attendance.db")
    print("=" * 45)

