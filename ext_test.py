#!/usr/bin/env python

import logging
import os
import csv

from blocks.model import Model
from blocks.extensions import SimpleExtension

logger = logging.getLogger(__name__)

class RunOnTest(SimpleExtension):
    def __init__(self, model_name, model, stream, **kwargs):
        super(RunOnTest, self).__init__(**kwargs)

        self.model_name = model_name

        cg = Model(model.predict(**stream.inputs()))

        self.inputs = cg.inputs
        self.outputs = model.predict.outputs

        req_vars_test = model.predict.inputs + ['trip_id']
        self.test_stream = stream.test(req_vars_test)

        self.function = cg.get_theano_function()

    def do(self, which_callback, *args):
        iter_no = repr(self.main_loop.log.status['iterations_done'])
        if 'valid_destination_cost' in self.main_loop.log.current_row:
            dvc = self.main_loop.log.current_row['valid_destination_cost']
        else:
            dvc = self.main_loop.log.current_row['valid_model_cost_cost']
        if 'valid_time_cost' in self.main_loop.log.current_row:
            tvc = self.main_loop.log.current_row['valid_time_cost']
        else:
            tvc = self.main_loop.log.current_row['valid_model_cost_cost']

        if 'destination' in self.outputs:
            dest_outname = 'test-dest-%s-it%s-cost%.3f.csv' % (self.model_name, iter_no, dvc)
            dest_outfile = open(os.path.join('output', dest_outname), 'w')
            dest_outcsv = csv.writer(dest_outfile)
            dest_outcsv.writerow(["TRIP_ID", "LATITUDE", "LONGITUDE"])
            logger.info("Generating output for test set: %s" % dest_outname)
        if 'duration' in self.outputs:
            time_outname = 'test-time-%s-it%s-cost%.3f.csv' % (self.model_name, iter_no, tvc)
            time_outfile = open(os.path.join('output', time_outname), 'w')
            time_outcsv = csv.writer(time_outfile)
            time_outcsv.writerow(["TRIP_ID", "TRAVEL_TIME"])
            logger.info("Generating output for test set: %s" % time_outname)

        for d in self.test_stream.get_epoch_iterator(as_dict=True):
            input_values = [d[k.name] for k in self.inputs]
            output_values = self.function(*input_values)
            if 'destination' in self.outputs:
                destination = output_values[self.outputs.index('destination')]
                dest_outcsv.writerow([d['trip_id'][0], destination[0, 0], destination[0, 1]])
            if 'duration' in self.outputs:
                duration = output_values[self.outputs.index('duration')]
                time_outcsv.writerow([d['trip_id'][0], int(round(duration[0]))])

        if 'destination' in self.outputs:
            dest_outfile.close()
        if 'duration' in self.outputs:
            time_outfile.close()

