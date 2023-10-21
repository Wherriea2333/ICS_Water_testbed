import argparse
from sim.Simulator import Simulator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build and run SCADA simulated environments')
    parser.add_argument(
        '-c', '--config', help='YAML configuration file to load', required=True)
    parser.add_argument('-v', '--verbose', help='Set verbosity level',
                        type=int, default=0, choices=[0, 1, 2], action='store')
    args = parser.parse_args()

    sim = Simulator(debug=args.verbose)
    sim.load_yml(args.config)

    sim.start()
