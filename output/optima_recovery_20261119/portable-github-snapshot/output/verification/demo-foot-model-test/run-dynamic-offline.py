from pathlib import Path
import runpy
import sys

repo = Path(__file__).resolve().parents[3]
engine = repo / 'Gait-lab-Vicon-to-QTM'
sys.path.insert(0, str(engine))
import gapi
gapi.grpc_send_command = lambda *_args, **_kwargs: None
sys.argv[0] = str(engine / 'Py3_DynamicMain.py')
runpy.run_path(sys.argv[0], run_name='__main__')
