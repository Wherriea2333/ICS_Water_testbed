import argparse

from Simulator import Simulator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build and run SCADA simulated environments')
    parser.add_argument(
        '-c', '--config', help='YAML configuration file to load', required=True)
    parser.add_argument('-v', '--verbose', help='Set verbosity level',
                        type=int, default=0, choices=[0, 1, 2], action='store')

    parser.add_argument('-m', '--math_parser', help='Type of math expression parser',
                        default='proportional', choices=['proportional', 'sympy', 'wolfram'], action='store')
    parser.add_argument('-g', '--generate', help='Generate openPLC ladder logic files', action='store_true')

    args = parser.parse_args()

    sim = Simulator(debug=args.verbose, math_parser=args.math_parser)
    sim.load_yml(args.config)
    if args.generate:
        sim.generate_st_files()
    else:
        sim.start()
