# sgPayNowQR65

A production-ready Python toolkit designed to mass-generate PayNow QR codes for Singapore mobile phone numbers.

## Features
- **Mass Generation:** Can iterate through custom ranges (e.g., millions) of Singapore phone numbers and generate a compliant EMV PayNow QR code for each.
- **Resilient Checkpointing:** Progress is saved automatically to `checkpoint.pkl`. If the script is interrupted (e.g., power loss or user termination), you can resume exactly where you left off.
- **Custom Logo Integration:** Automatically places a central logo (like a PayNow logo) onto the QR codes for better branding and trust.
- **Performant & Robust:** Engineered with $O(1)$ operations for tracking tasks, allowing it to efficiently compute large sets of numbers without heavy memory footprints or degradation.
- **Interactive CLI Launcher:** Easy to use batch menus that let you manage the script and configure generation ranges cleanly.

## Prerequisites
- Python 3.8+
- Windows (batch scripts are natively supported, but Python scripts work cross-platform)

## Setup & Usage

### 1. Setup the Environment
Simply run the `setup.bat` file. This will automatically:
- Create a `.venv` (Python Virtual Environment).
- Upgrade `pip`.
- Install all necessary dependencies from `requirements.txt` (like `Pillow` and `qrcode`).

### 2. Generate QR Codes
Run the `run_script.bat` file. You will be greeted with an interactive menu:

1. **Run / Resume (Default Settings):** Runs the script for the default range (80000000 - 99999999). If a checkpoint is detected, it automatically resumes.
2. **Start New Custom Range:** Prompts you for a specific start and end phone number. WARNING: Choosing this will reset any existing checkpoint.
3. **Delete Checkpoint Only:** Safely removes the checkpoint file.

### 3. Output Directory
The script leverages `download_path_manager.py` to securely prompt for the output folder for your QR codes. The directory will be validated and automatically created for you.

## Configuration
You can edit `generatePayNowQR.py` constants directly to configure defaults:
- `START_PHONE_NUM` / `END_PHONE_NUM`
- `QR_FILL_RGB`: Changes the QR code primary color.
- `LOGO_FILENAME`: Set to `paynow_logo.png` by default. Place the image next to the script to embed it inside the QR code automatically.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
