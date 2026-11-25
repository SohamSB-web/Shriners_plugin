# -*- coding: utf-8 -*-
"""
<One of the file associated with the Program to compute lower extremity Shrine Gait Model kinematics and kinetics>
Copyright (C) 2023  <Anas Fodkar>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
# Static Model computes posture and stores Technical to Anatomical Coordinate Transformaion

Created on Thu Feb 01 11:09:51 2018
Last Update: Aug 26, 2024

@author: psaraswat
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter


class _Tee:
    def __init__(self, stream, log):
        self.stream, self.log = stream, log

    def write(self, text):
        self.stream.write(text)
        return self.log.write(text)

    def flush(self):
        self.stream.flush()
        self.log.flush()


def main(argv=None):
    started = perf_counter()
    parser = argparse.ArgumentParser(description="Headless Shriners static calibration")
    parser.add_argument('--TestingCondition', '-t', default='BF')
    parser.add_argument('--sessionPath', '-s', required=True, help='Path to session.xml')
    parser.add_argument('--filename', '-f', required=True, help='Local C3D or measurement filename in session.xml')
    parser.add_argument('--headless', action='store_true', help='Retained processing-service interface; all runs are headless')
    parser.add_argument('--reportPath', help='Optional destination for the existing static PDF report')
    parser.add_argument('--publish-qtm', action='store_true',
                        help='Also publish modeled markers to QTM; requires the intended static measurement to be open')
    args = parser.parse_args(argv)
    log_dir = Path(__file__).resolve().parents[1] / 'logs' / 'static'
    log_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', prefix='static-', suffix='.log',
                                     dir=log_dir, delete=False) as log:
        print('[log] Full static diagnostic log: ' + log.name, flush=True)
        with redirect_stdout(_Tee(sys.stdout, log)), redirect_stderr(_Tee(sys.stderr, log)):
            print('[invocation] ' + json.dumps(dict(executable=sys.executable, cwd=os.getcwd(),
                  arguments=list(argv) if argv is not None else sys.argv[1:],
                  environment={key: os.environ.get(key) for key in (
                      'CONDA_PREFIX', 'QT_QPA_PLATFORM', 'SHRINERS_NON_INTERACTIVE', 'SHRINERS_AUTO_SELECT_CYCLE')})), flush=True)
            return _run(args, started)


def _run(args, started):
    try:
        from static_calibration_engine import run_static_calibration
        print('[startup] Imports: %.6f s' % (perf_counter() - started), flush=True)
        result = run_static_calibration(args.sessionPath, args.filename, args.TestingCondition,
                                        progress=lambda message: print(message, flush=True),
                                        report_path=args.reportPath, publish_qtm=args.publish_qtm)
        return 0 if result.success else 2
    except Exception as error:
        print('[error] Static calibration failed: ' + str(error), flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
