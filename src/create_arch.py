#!/usr/bin/env python3
# Author: Ethan Sifferman
# Description: Custom architecture file is created from Jinja template

import sys
import os
import jinja2



def create_arch(num_inputs, num_outputs, channelfrac_inputs, channelfrac_outputs):
    template_path = './templates/arch.xml' # currently only compatible with VPR 8.0.0
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(os.path.abspath(__file__))))
    template = env.get_template(template_path)
    return template.render(
        NUM_INPUTS=num_inputs,
        NUM_OUTPUTS=num_outputs,
        CHANNELFRAC_INPUTS=channelfrac_inputs,
        CHANNELFRAC_OUTPUTS=channelfrac_outputs
    )



def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <num inputs> <num outputs> > arch.xml')
        return 1

    num_inputs, num_outputs, channelfrac_inputs, channelfrac_outputs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

    try:
        num_inputs = int(num_inputs)
        num_outputs = int(num_outputs)
    except ValueError:
        print('Error: Please provide valid integer inputs for <num inputs> and <num outputs>.')
        return 1
    try:
        channelfrac_inputs = float(channelfrac_inputs)
        channelfrac_outputs = float(channelfrac_outputs)
    except ValueError:
        print('Error: Please provide valid float inputs for <channelfrac inputs> and <channelfrac_outputs>.')
        return 1

    try:
        result = create_arch(num_inputs, num_outputs, channelfrac_inputs, channelfrac_outputs)
        print(result)
        return 0
    except Exception as e:
        print(f'Error: {e}')
        return 1



if __name__ == '__main__':
    sys.exit( main() )
