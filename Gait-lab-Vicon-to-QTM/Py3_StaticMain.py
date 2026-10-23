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
import json
import sys
from time import perf_counter


def main(argv=None):
    started = perf_counter()
    parser = argparse.ArgumentParser(description="Headless Shriners static calibration")
    parser.add_argument('--TestingCondition', '-t', default='BF')
    parser.add_argument('--sessionPath', '-s', required=True, help='Path to session.xml')
    parser.add_argument('--filename', '-f', required=True, help='Measurement filename in session.xml')
    parser.add_argument('--headless', action='store_true', help='Retained processing-service interface; all runs are headless')
    parser.add_argument('--reportPath', help='Optional destination for the existing static PDF report')
    args = parser.parse_args(argv)
    try:
        from static_calibration_engine import run_static_calibration
        print('[startup] Imports: %.6f s' % (perf_counter() - started), flush=True)
        result = run_static_calibration(args.sessionPath, args.filename, args.TestingCondition,
                                        progress=lambda message: print(message, flush=True),
                                        report_path=args.reportPath)
        return 0 if result.success else 2
    except Exception as error:
        print('[error] Static calibration failed: ' + str(error), flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
