from pathlib import Path

MAC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MAC_DIR.parent

# Institute Name that is printed on top of pdf pages
InstituteName   = 'Motion Analysis Center'
# Global path for Patients Data directory containing patient folders and sessions
PatientsDataLocation = str(PROJECT_ROOT / "Shriners_Gait_Model_PAF_v1.0" / "Shriners_Gait_Model_PAF_v1.0" / "Data")
# Initial Path for where Vicon session GCD files are located 
ViconFilesLocation = './'
# Path for where File selection and other information will be stored 
DisplaySettingsFileLocation = str(MAC_DIR / "DisplaySettingsLocation")
# For GDI Features File Names. GDI is computed if not found in GCD file.
GDIFeaturesFileName = str(MAC_DIR / "mmc1-Shriners.xls")
# Initial Path for where Pdf can be stored.
InitialPathForPdf = 'C:/Custom/PDF/Output'
# Path for walking norm GCD
NormAveGCDFileName = str(MAC_DIR / "TD_Ave.GCD")
# Path for running norm GCD
NormRunAveGCDFileName = str(MAC_DIR / "TD_Run_Ave.GCD")
# Path for QTM-GRPC directory
QtmGrpcLocation = str(PROJECT_ROOT / "QTM-GRPC")
# Flag for whether to use Greenville Folder Structure for storing Pdfs
UseGreenvilleFolderStructure = False
# Default selection for Whether to use MostRepresentative (MR) or Average (Ave) trial for kinematics. It can be changed in GUI.
MRorAve = 'MR'
# Minimum Value when EMG is assumed to be available in GCD data
EMG_MinOn = 0.5
