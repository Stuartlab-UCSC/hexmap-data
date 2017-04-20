
# placeNode_web.py
# For the placeNode calculation this handles:
#   - validation of received input
#   - mapping between mapID and layout to data file locations
#   - http response and code

import os.path, json, types, requests, traceback, logging
from argparse import Namespace
from flask import Response
from webUtil import SuccessResp, ErrorResp, getMetaData, \
    availableMapLayouts, validateMap, validateLayout, validateEmail, \
    validateViewServer
import placeNode
import compute_sparse_matrix
import utils
import pandas as pd
import StringIO
import numpy as np

def validateParameters(data):

    # Validate an overlayNodes query

    # Basic checks on required parameters
    validateMap(data, True)
    validateLayout(data, True)
    if 'nodes' not in data:
        raise ErrorResp('nodes parameter missing or malformed')
    if not isinstance(data['nodes'], dict):
        raise ErrorResp('nodes parameter should be a dictionary')
    if len(data['nodes'].keys()) < 1:
        raise ErrorResp('there are no nodes in the nodes dictionary')
    
    # Check for non-printable chars in names
    # TODO
    
    # Basic checks on optional parameters
    validateEmail(data)
    validateViewServer(data)
    if 'neighborCount' in data and \
        (not isinstance(data['neighborCount'], int) or \
        data['neighborCount'] < 1):
        raise ErrorResp('neighborCount parameter should be a positive integer')

    # Check that map and layout are available for n-of-1 analysis
    mapLayouts = availableMapLayouts('Nof1')
    if not data['map'] in mapLayouts:
        raise ErrorResp(
            'Map does not have any layouts with background data: ' +
            data['map'])
    if not data['layout'] in mapLayouts[data['map']]:
        raise ErrorResp('Layout does not have background data: ' +
            data['layout'])

def createBookmark(state, viewServer, ctx):

    # Create a bookmark

    # Ask the view server to create a bookmark of this client state
    # TODO fix the request to the view server
    try:
        bResult = requests.post(
            viewServer + '/query/createBookmark',
            #cert=(ctx['sslCert'], ctx['sslKey']),
            verify=False,
            headers = { 'Content-type': 'application/json' },
            data = json.dumps(state)
        )
    except:
        raise ErrorResp('Unknown error connecting to view server: ' +
            viewServer)

    bData = json.loads(bResult.text)
    if bResult.status_code == 200:
        return bData
    else:
        raise ErrorResp(bData)

def calcComplete(result, ctx):

    # The calculation has completed, so create bookmarks and send email
    
    dataIn = ctx['dataIn']

    #logging.debug('calcComplete: result: ' + str(result))
    
    if 'error' in result:
        raise ErrorResp(result['error'])

    # Be sure we have a view server
    if not 'viewServer' in dataIn:
        dataIn['viewServer'] = ctx['viewerUrl']

    # TODO find the firstAttribute in Layer_Data_Types.tab
    if 'firstAttribute' in ctx['meta']:
        firstAttr = ctx['meta']['firstAttribute']
    else:
        firstAttr = None

    # TODO find the layoutIndex from layouts.tab
    layoutIndex = 0
    if dataIn['map'] == 'Pancan12/SampleMap':
        layouts = [
            'mRNA',
            'miRNA',
            'RPPA',
            'Methylation',
            'SCNV',
            'Mutations',
            'PARADIGM (inferred)',
        ]
        layoutIndex = layouts.index(dataIn['layout'])

    # Format the result as client state in preparation to create a bookmark
    state = {
        'page': 'mapPage',
        'project': dataIn['map'] + '/',
        'layoutIndex': layoutIndex,
        'shortlist': [firstAttr],
        'first_layer': [firstAttr],
        'overlayNodes': {},
        'dynamic_attrs': {},
    }

    # Populate state for each node
    for node in result['nodes']:
        nData = result['nodes'][node]
        state['overlayNodes'][node] = { 'x': nData['x'], 'y': nData['y'] }
        
        # Build the neighbor places layer
        attr = node + ': ' + dataIn['layout'] + ': neighbors'
        state['shortlist'].append(attr)
        state['dynamic_attrs'][attr] = {
            'dynamic': True,
            'datatype': 'binary',
            'data': {},
        }
        
        # Build the neighbor values layer
        attrV = node + ': ' + dataIn['layout'] + ': neighbor values'
        state['shortlist'].append(attrV)
        state['dynamic_attrs'][attrV] = {
            'dynamic': True,
            'datatype': 'continuous',
            'data': {},
        }
        
        # Add the values to the new layers
        for neighbor in nData['neighbors']:
            state['dynamic_attrs'][attr]['data'][neighbor] = 1;
            state['dynamic_attrs'][attrV]['data'][neighbor] = \
                nData['neighbors'][neighbor];

        # If individual Urls were requested, create a bookmark for this node
        if 'individualUrls' in dataIn and dataIn['individualUrls']:
            bData = createBookmark(state, dataIn['viewServer'], ctx)
            result['nodes'][node]['url'] = bData['bookmark']

            # Clear the node data to get ready for the next node
            state['overlayNodes'] = {}
            state['dynamic_attrs'] = {}
        
    # If individual urls were not requested, create one bookmark containing all
    # nodes and return that url for each node
    if not 'individualUrls' in dataIn or not dataIn['individualUrls']:
        bData = createBookmark(state, dataIn['viewServer'], ctx)
        for node in result['nodes']:
            result['nodes'][node]['url'] = bData['bookmark']

    # TODO: Send completion Email
    """
    # a javascript routine:
    // Send email to interested parties
    var subject = 'tumor map results: ',
        msg = 'Tumor Map results are ready to view at:\n\n';
    
    _.each(emailUrls, function (node, nodeName) {
        msg += nodeName + ' : ' + node + '\n';
        subject += node + '  ';
    });
        
    if ('email' in dataIn) {
        sendMail(dataIn.email, subject, msg);
        msg += '\nAlso sent to: ' + dataIn.email;
    } else {
        msg += '\nNo emails included in request';
    }
    sendMail(ADMIN_EMAIL, subject, msg);
    """

    return result

def outputToDict(neighboorhood, xys, urls):
    '''
    This function takes the output from the newplacement call
      into the expected format
    @param neighboorhood: pandas df
    @param xys: pandas df
    @param urls: an array of URLs
    @return: dictionary to be turned into a JSON str
    '''
    #return dictionary to populate with results
    retDict = {"nodes":{}}

    #seperating the columns of the neighborhood df
    # for processing
    newNodes  = neighboorhood[neighboorhood.columns[0]]
    neighbors = neighboorhood[neighboorhood.columns[1]]
    scores    = neighboorhood[neighboorhood.columns[2]]
    #grab column names for indexing
    xcol = xys.columns[0]
    ycol = xys.columns[1]

    for i,node in enumerate(set(newNodes)):
        maskArr = np.array(newNodes == node)
        retDict['nodes'][node] = {}
        retDict['nodes'][node]['neighbors'] = dict(zip(neighbors.iloc[maskArr],
                                                       scores.iloc[maskArr]))
        #add urls to the return struct
        #retDict['nodes'][node]['url'] = urls[i]
        retDict['nodes'][node]['x'] = xys.loc[node,xcol]
        retDict['nodes'][node]['y'] = xys.loc[node,ycol]

    return retDict

def putDataIntoPythonStructs(featurePath,xyPath,nodesDict):
    '''
    takes in the filenames and nodes dictionary needed for placement calc
    @param featurePath:
    @param xyPath:
    @param tabSepArray:
    @return:
    '''
    return (compute_sparse_matrix.numpyToPandas(
            *compute_sparse_matrix.read_tabular(featurePath)
                                                ),
            utils.readXYs(xyPath),
            nodesToPandas(nodesDict)
          )

def nodesToPandas(pydict):
    '''
    input the json['nodes'] structure and outputs pandas df
    This looks crazy because we needed to read in the new node data
    in the same way as the original feature matrix.
    @param pydict: the dataIn['nodes'] structure,
                   currently a dict of dicts {columns -> {rows -> values}}
    @return: a pandas dataframe
    '''
    df = pd.DataFrame(pydict)
    s_buf = StringIO.StringIO()
    #dump pandas data frame into buffer
    df.to_csv(s_buf,sep='\t')
    s_buf.seek(0)
    return compute_sparse_matrix.numpyToPandas(
            *compute_sparse_matrix.read_tabular(s_buf)
                                                )

if __debug__:
    def calcTestStub(newNodes):
        #print 'opts.newNodes', opts.newNodes
        if 'testError' in newNodes:
            return {
                'error': 'Some error message or stack trace'
            }
        elif len(newNodes) == 1:
            return {'nodes': {
                'newNode1': {
                    'x': 73,
                    'y': 91,
                    'neighbors': {
                        'TCGA-BP-4790': 0.352,
                        'TCGA-AK-3458': 0.742,
                    }
                },
            }}
        elif len(newNodes) > 1:
            return {'nodes': {
                'newNode1': {
                    'x': 73,
                    'y': 91,
                    'neighbors': {
                        'TCGA-BP-4790': 0.352,
                        'TCGA-AK-3458': 0.742,
                    }
                },
                'newNode2': {
                    'x': 53,
                    'y': 47,
                    'neighbors': {
                        'neighbor1': 0.567,
                        'neighbor2': 0.853,
                    }
                },
            }}
        else:
            return { 'error': 'unknown test' }

def calc(dataIn, ctx):

    # The entry point from the www URL routing

    validateParameters(dataIn)

    # Find the Nof1 data files for this map and layout
    meta = getMetaData(dataIn['map'], ctx)
    
    files = meta['layouts'][dataIn['layout']]
    
    if not 'testStub' in dataIn:
    
        # Check to see if the data files exist
        # TODO: test both of these checks
        if not os.path.exists(files['fullFeatureMatrix']):
            raise ErrorResp('full feature matrix file not found: ' +
                files['fullFeatureMatrix'], 500)
        if not os.path.exists(files['xyPositions']):
            raise ErrorResp('xy positions file not found: ' +
                files['xyPositions'], 500)

    
    # Set any optional parms, letting the calc script set defaults.
    if 'neighborCount' in dataIn:
        top = dataIn['neighborCount']
    else:
        top = 6

    #logging.debug('opts: ' + str(opts));

    if 'testStub' in dataIn:
        result = calcTestStub(dataIn['nodes'])
        
    else:

        #make expected python data structs
        referenceDF, xyDF, newNodesDF = \
         putDataIntoPythonStructs(files['fullFeatureMatrix'],
                                  files['xyPositions'],
                                  dataIn['nodes'])
        # Call the calc script.
        neighboorhood, xys, urls = placeNode.placeNew(newNodesDF,referenceDF,
                                                      xyDF,top,dataIn['map'],
                                                      num_jobs=1)
        #format into JSON-like struct
        result = outputToDict(neighboorhood,xys,urls)


    ctx['dataIn'] = dataIn
    ctx['meta'] = meta
    return calcComplete(result, ctx)
