"""
statsNoLayout.py: Run the sample-based statistics.
"""
import sys, os, numpy, subprocess, shutil, tempfile, pprint
import tsv, csv, datetime, time, math, multiprocessing
import pool, traceback
from statsLayer import ForEachLayer

def timestamp():
    return str(datetime.datetime.now())[8:-7]

def subprocessPerLayer(layer_names, parm):

    # Spawn the subprocesses to calculate stats for each layer
    # The number of pairs to compare including compare to self
    pairCount = len(parm['statsLayers']) ** 2
    pool.hostProcessorMsg()
    print 'Starting to build', pairCount, 'layer pairs...'

    """
    # TODO easy testing without subprocesses
    for layerA in parm['statsLayers']:
        parm['layerA'] = layerA
        parm['layerIndex'] = layer_names.index(layerA)
        oneLayer = ForEachLayer(parm)
        oneLayer()
    """
    
    # Handle the stats for each layer, in parallel
    allLayers = []
    for layerA in parm['statsLayers']:
        parm['layerA'] = layerA
        parm['layerIndex'] = layer_names.index(layerA)
        allLayers.append(ForEachLayer(parm))

    print pool.hostProcessorMsg()
    print len(parm['statsLayers']), 'subprocesses to run, one per layer.'
    pool.runSubProcesses(allLayers)

def statsNoLayout(layers, layer_names, ctx, options):
    """
    The tool will deploy the appropriate association stat test on each
    array of layers, computing the p-value between pairs of attributes.
    @param layers: the global layers object
    @param layer_names: list of layer names to be included in these stats
    @param ctx: global context for hexagram.py
    @param options: those options passed into hexagram.py

    The values generated from each individual stats test will be printed to
    separate files. On the client-side the user will be asked to select what 
    types of values they want to correlate their selected attribute against.
    """
    
    print timestamp(), "Running sample-based statistics..."

    # Consider all data types for pre-computed stats
    statsLayers = ctx.binary_layers \
        + ctx.categorical_layers \
        + ctx.continuous_layers

    # Create the parameters to pass to the subprocesses.
    parm = {
        'hexNames': ctx.all_hexagons[0].values(), # a list of all hexagon names
        'layers': layers, # all layers
        'directory': options.directory,
        'statsLayers': statsLayers,
        'binLayers': ctx.binary_layers,
        'catLayers': ctx.categorical_layers,
        'contLayers': ctx.continuous_layers,
        'temp_dir': tempfile.mkdtemp(), # the dir to store temporary working files,
    }

    # Spawn the layer processes
    num_layers = len(parm['statsLayers'])
    print timestamp(), "Processing", num_layers, "layers"
    subprocessPerLayer(layer_names, parm)

    print timestamp(), "Sample-based statistics complete"

    return True    
