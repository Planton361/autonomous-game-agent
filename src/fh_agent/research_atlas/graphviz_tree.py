"""Pinned Graphviz 13.1.0 DOT→SVG output; regenerate only after source/layout review.

Build tool: @hpcc-js/wasm-graphviz 1.9.0 (temporary tool, no runtime dependency).
Input: diagram_svg.architecture_dot(validated_atlas), UTF-8; Graphviz.dot(input).
Postprocessing: remove XML/DTD header; add accessibility and provenance metadata.
The generator checks the complete DOT hash before emitting these fixed bytes.
"""

DOT_SHA256 = "4ead772bb6ee7d88fe2202a83a464183e69a7c04e6fc83b2749418a6a77e3a15"
SVG = (
    '<svg role="img" aria-labelledby="tree-title tree-desc" width'
    '="4085pt" height="470pt"\n viewBox="0.00 0.00 4085.00 470.00"'
    ' xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.'
    'w3.org/1999/xlink">\n<title id="tree-title">Architecture Tree'
    ' · one System and 28 Components</title>\n<desc id="tree-desc"'
    ">Top-down containment only; open at full size and zoom. Comp"
    "lete preferred links in Markdown.</desc>\n<metadata>Graphviz "
    "13.1.0; @hpcc-js/wasm-graphviz 1.9.0; Arial; DOT SHA-256 4ea"
    "d772bb6ee7d88fe2202a83a464183e69a7c04e6fc83b2749418a6a77e3a1"
    '5</metadata>\n<g id="graph0" class="graph" transform="scale(1'
    ' 1) rotate(0) translate(21.6 448.64)">\n<title>Architecture</'
    'title>\n<polygon fill="#ffffff" stroke="none" points="-21.6,2'
    '1.6 -21.6,-448.64 4063.05,-448.64 4063.05,21.6 -21.6,21.6"/>'
    '\n<!-- CMP&#45;BODY -->\n<g id="CMP&#45;BODY" class="node">\n<t'
    'itle>CMP&#45;BODY</title>\n<path fill="#edf5fc" stroke="#2d69'
    '94" d="M171.46,-254.56C171.46,-254.56 66.48,-254.56 66.48,-2'
    "54.56 60.48,-254.56 54.48,-248.56 54.48,-242.56 54.48,-242.5"
    "6 54.48,-184.48 54.48,-184.48 54.48,-178.48 60.48,-172.48 66"
    ".48,-172.48 66.48,-172.48 171.46,-172.48 171.46,-172.48 177."
    "46,-172.48 183.46,-178.48 183.46,-184.48 183.46,-184.48 183."
    "46,-242.56 183.46,-242.56 183.46,-248.56 177.46,-254.56 171."
    '46,-254.56"/>\n<text xml:space="preserve" text-anchor="middle'
    '" x="118.97" y="-229.72" font-family="Arial" font-size="18.0'
    '0" fill="#21384b">Body</text>\n<text xml:space="preserve" tex'
    't-anchor="middle" x="118.97" y="-208.12" font-family="Arial"'
    ' font-size="18.00" fill="#21384b">CMP&#45;BODY</text>\n<text '
    'xml:space="preserve" text-anchor="middle" x="118.97" y="-186'
    '.52" font-family="Arial" font-size="18.00" fill="#21384b">im'
    "plemented</text>\n</g>\n<!-- CMP&#45;BOUNDED&#45;REFLEX -->\n<g"
    ' id="CMP&#45;BOUNDED&#45;REFLEX" class="node">\n<title>CMP&#4'
    '5;BOUNDED&#45;REFLEX</title>\n<path fill="#edf5fc" stroke="#2'
    'd6994" d="M225.94,-92.88C225.94,-92.88 12,-92.88 12,-92.88 6'
    ",-92.88 0,-86.88 0,-80.88 0,-80.88 0,-22.8 0,-22.8 0,-16.8 6"
    ",-10.8 12,-10.8 12,-10.8 225.94,-10.8 225.94,-10.8 231.94,-1"
    "0.8 237.94,-16.8 237.94,-22.8 237.94,-22.8 237.94,-80.88 237"
    '.94,-80.88 237.94,-86.88 231.94,-92.88 225.94,-92.88"/>\n<tex'
    't xml:space="preserve" text-anchor="middle" x="118.97" y="-6'
    '8.04" font-family="Arial" font-size="18.00" fill="#21384b">B'
    'ounded Reflex</text>\n<text xml:space="preserve" text-anchor='
    '"middle" x="118.97" y="-46.44" font-family="Arial" font-size'
    '="18.00" fill="#21384b">CMP&#45;BOUNDED&#45;REFLEX</text>\n<t'
    'ext xml:space="preserve" text-anchor="middle" x="118.97" y="'
    '-24.84" font-family="Arial" font-size="18.00" fill="#21384b"'
    ">target&#45;only</text>\n</g>\n<!-- CMP&#45;BODY&#45;&gt;CMP&#"
    '45;BOUNDED&#45;REFLEX -->\n<g id="part_of:CMP&#45;BOUNDED&#45'
    ';REFLEX:CMP&#45;BODY" class="edge">\n<title>CMP&#45;BODY&#45;'
    '&gt;CMP&#45;BOUNDED&#45;REFLEX</title>\n<path fill="none" str'
    'oke="#526677" stroke-width="1.5" d="M118.97,-172.23C118.97,-'
    '148.02 118.97,-117.33 118.97,-93.12"/>\n</g>\n<!-- CMP&#45;BOD'
    'Y&#45;CERTIFICATION -->\n<g id="CMP&#45;BODY&#45;CERTIFICATIO'
    'N" class="node">\n<title>CMP&#45;BODY&#45;CERTIFICATION</titl'
    'e>\n<path fill="#edf5fc" stroke="#2d6994" d="M456.43,-265.36C'
    "456.43,-265.36 213.51,-265.36 213.51,-265.36 207.51,-265.36 "
    "201.51,-259.36 201.51,-253.36 201.51,-253.36 201.51,-173.68 "
    "201.51,-173.68 201.51,-167.68 207.51,-161.68 213.51,-161.68 "
    "213.51,-161.68 456.43,-161.68 456.43,-161.68 462.43,-161.68 "
    "468.43,-167.68 468.43,-173.68 468.43,-173.68 468.43,-253.36 "
    '468.43,-253.36 468.43,-259.36 462.43,-265.36 456.43,-265.36"'
    '/>\n<text xml:space="preserve" text-anchor="middle" x="334.97'
    '" y="-240.52" font-family="Arial" font-size="18.00" fill="#2'
    '1384b">Body Validation /</text>\n<text xml:space="preserve" t'
    'ext-anchor="middle" x="334.97" y="-218.92" font-family="Aria'
    'l" font-size="18.00" fill="#21384b">Certification</text>\n<te'
    'xt xml:space="preserve" text-anchor="middle" x="334.97" y="-'
    '197.32" font-family="Arial" font-size="18.00" fill="#21384b"'
    '>CMP&#45;BODY&#45;CERTIFICATION</text>\n<text xml:space="pres'
    'erve" text-anchor="middle" x="334.97" y="-175.72" font-famil'
    'y="Arial" font-size="18.00" fill="#21384b">target&#45;only</'
    'text>\n</g>\n<!-- CMP&#45;CORTEX -->\n<g id="CMP&#45;CORTEX" cl'
    'ass="node">\n<title>CMP&#45;CORTEX</title>\n<path fill="#edf5f'
    'c" stroke="#2d6994" d="M621.43,-254.56C621.43,-254.56 498.51'
    ",-254.56 498.51,-254.56 492.51,-254.56 486.51,-248.56 486.51"
    ",-242.56 486.51,-242.56 486.51,-184.48 486.51,-184.48 486.51"
    ",-178.48 492.51,-172.48 498.51,-172.48 498.51,-172.48 621.43"
    ",-172.48 621.43,-172.48 627.43,-172.48 633.43,-178.48 633.43"
    ",-184.48 633.43,-184.48 633.43,-242.56 633.43,-242.56 633.43"
    ',-248.56 627.43,-254.56 621.43,-254.56"/>\n<text xml:space="p'
    'reserve" text-anchor="middle" x="559.97" y="-229.72" font-fa'
    'mily="Arial" font-size="18.00" fill="#21384b">Cortex</text>\n'
    '<text xml:space="preserve" text-anchor="middle" x="559.97" y'
    '="-208.12" font-family="Arial" font-size="18.00" fill="#2138'
    '4b">CMP&#45;CORTEX</text>\n<text xml:space="preserve" text-an'
    'chor="middle" x="559.97" y="-186.52" font-family="Arial" fon'
    't-size="18.00" fill="#21384b">implemented</text>\n</g>\n<!-- C'
    'MP&#45;EVIDENCE&#45;LEDGER -->\n<g id="CMP&#45;EVIDENCE&#45;L'
    'EDGER" class="node">\n<title>CMP&#45;EVIDENCE&#45;LEDGER</tit'
    'le>\n<path fill="#edf5fc" stroke="#2d6994" d="M882.94,-254.56'
    "C882.94,-254.56 662.99,-254.56 662.99,-254.56 656.99,-254.56"
    " 650.99,-248.56 650.99,-242.56 650.99,-242.56 650.99,-184.48"
    " 650.99,-184.48 650.99,-178.48 656.99,-172.48 662.99,-172.48"
    " 662.99,-172.48 882.94,-172.48 882.94,-172.48 888.94,-172.48"
    " 894.94,-178.48 894.94,-184.48 894.94,-184.48 894.94,-242.56"
    " 894.94,-242.56 894.94,-248.56 888.94,-254.56 882.94,-254.56"
    '"/>\n<text xml:space="preserve" text-anchor="middle" x="772.9'
    '7" y="-229.72" font-family="Arial" font-size="18.00" fill="#'
    '21384b">Evidence Ledger</text>\n<text xml:space="preserve" te'
    'xt-anchor="middle" x="772.97" y="-208.12" font-family="Arial'
    '" font-size="18.00" fill="#21384b">CMP&#45;EVIDENCE&#45;LEDG'
    'ER</text>\n<text xml:space="preserve" text-anchor="middle" x='
    '"772.97" y="-186.52" font-family="Arial" font-size="18.00" f'
    'ill="#21384b">partial</text>\n</g>\n<!-- CMP&#45;INDEPENDENT&#'
    '45;VERIFIER -->\n<g id="CMP&#45;INDEPENDENT&#45;VERIFIER" cla'
    'ss="node">\n<title>CMP&#45;INDEPENDENT&#45;VERIFIER</title>\n<'
    'path fill="#edf5fc" stroke="#2d6994" d="M1190.94,-254.56C119'
    "0.94,-254.56 925,-254.56 925,-254.56 919,-254.56 913,-248.56"
    " 913,-242.56 913,-242.56 913,-184.48 913,-184.48 913,-178.48"
    " 919,-172.48 925,-172.48 925,-172.48 1190.94,-172.48 1190.94"
    ",-172.48 1196.94,-172.48 1202.94,-178.48 1202.94,-184.48 120"
    "2.94,-184.48 1202.94,-242.56 1202.94,-242.56 1202.94,-248.56"
    ' 1196.94,-254.56 1190.94,-254.56"/>\n<text xml:space="preserv'
    'e" text-anchor="middle" x="1057.97" y="-229.72" font-family='
    '"Arial" font-size="18.00" fill="#21384b">Independent Verifie'
    'r</text>\n<text xml:space="preserve" text-anchor="middle" x="'
    '1057.97" y="-208.12" font-family="Arial" font-size="18.00" f'
    'ill="#21384b">CMP&#45;INDEPENDENT&#45;VERIFIER</text>\n<text '
    'xml:space="preserve" text-anchor="middle" x="1057.97" y="-18'
    '6.52" font-family="Arial" font-size="18.00" fill="#21384b">i'
    "mplemented</text>\n</g>\n<!-- CMP&#45;INPUT&#45;EXECUTOR -->\n<"
    'g id="CMP&#45;INPUT&#45;EXECUTOR" class="node">\n<title>CMP&#'
    '45;INPUT&#45;EXECUTOR</title>\n<path fill="#edf5fc" stroke="#'
    '2d6994" d="M1440.93,-254.56C1440.93,-254.56 1233.01,-254.56 '
    "1233.01,-254.56 1227.01,-254.56 1221.01,-248.56 1221.01,-242"
    ".56 1221.01,-242.56 1221.01,-184.48 1221.01,-184.48 1221.01,"
    "-178.48 1227.01,-172.48 1233.01,-172.48 1233.01,-172.48 1440"
    ".93,-172.48 1440.93,-172.48 1446.93,-172.48 1452.93,-178.48 "
    "1452.93,-184.48 1452.93,-184.48 1452.93,-242.56 1452.93,-242"
    '.56 1452.93,-248.56 1446.93,-254.56 1440.93,-254.56"/>\n<text'
    ' xml:space="preserve" text-anchor="middle" x="1336.97" y="-2'
    '29.72" font-family="Arial" font-size="18.00" fill="#21384b">'
    'InputExecutor</text>\n<text xml:space="preserve" text-anchor='
    '"middle" x="1336.97" y="-208.12" font-family="Arial" font-si'
    'ze="18.00" fill="#21384b">CMP&#45;INPUT&#45;EXECUTOR</text>\n'
    '<text xml:space="preserve" text-anchor="middle" x="1336.97" '
    'y="-186.52" font-family="Arial" font-size="18.00" fill="#213'
    '84b">implemented</text>\n</g>\n<!-- CMP&#45;MANAGER -->\n<g id='
    '"CMP&#45;MANAGER" class="node">\n<title>CMP&#45;MANAGER</titl'
    'e>\n<path fill="#edf5fc" stroke="#2d6994" d="M1621.43,-254.56'
    "C1621.43,-254.56 1482.51,-254.56 1482.51,-254.56 1476.51,-25"
    "4.56 1470.51,-248.56 1470.51,-242.56 1470.51,-242.56 1470.51"
    ",-184.48 1470.51,-184.48 1470.51,-178.48 1476.51,-172.48 148"
    "2.51,-172.48 1482.51,-172.48 1621.43,-172.48 1621.43,-172.48"
    " 1627.43,-172.48 1633.43,-178.48 1633.43,-184.48 1633.43,-18"
    "4.48 1633.43,-242.56 1633.43,-242.56 1633.43,-248.56 1627.43"
    ',-254.56 1621.43,-254.56"/>\n<text xml:space="preserve" text-'
    'anchor="middle" x="1551.97" y="-229.72" font-family="Arial" '
    'font-size="18.00" fill="#21384b">Manager</text>\n<text xml:sp'
    'ace="preserve" text-anchor="middle" x="1551.97" y="-208.12" '
    'font-family="Arial" font-size="18.00" fill="#21384b">CMP&#45'
    ';MANAGER</text>\n<text xml:space="preserve" text-anchor="midd'
    'le" x="1551.97" y="-186.52" font-family="Arial" font-size="1'
    '8.00" fill="#21384b">implemented</text>\n</g>\n<!-- CMP&#45;MA'
    'NAGER&#45;GROUNDING -->\n<g id="CMP&#45;MANAGER&#45;GROUNDING'
    '" class="node">\n<title>CMP&#45;MANAGER&#45;GROUNDING</title>'
    '\n<path fill="#edf5fc" stroke="#2d6994" d="M959.43,-92.88C959'
    ".43,-92.88 702.51,-92.88 702.51,-92.88 696.51,-92.88 690.51,"
    "-86.88 690.51,-80.88 690.51,-80.88 690.51,-22.8 690.51,-22.8"
    " 690.51,-16.8 696.51,-10.8 702.51,-10.8 702.51,-10.8 959.43,"
    "-10.8 959.43,-10.8 965.43,-10.8 971.43,-16.8 971.43,-22.8 97"
    "1.43,-22.8 971.43,-80.88 971.43,-80.88 971.43,-86.88 965.43,"
    '-92.88 959.43,-92.88"/>\n<text xml:space="preserve" text-anch'
    'or="middle" x="830.97" y="-68.04" font-family="Arial" font-s'
    'ize="18.00" fill="#21384b">Grounding</text>\n<text xml:space='
    '"preserve" text-anchor="middle" x="830.97" y="-46.44" font-f'
    'amily="Arial" font-size="18.00" fill="#21384b">CMP&#45;MANAG'
    'ER&#45;GROUNDING</text>\n<text xml:space="preserve" text-anch'
    'or="middle" x="830.97" y="-24.84" font-family="Arial" font-s'
    'ize="18.00" fill="#21384b">implemented</text>\n</g>\n<!-- CMP&'
    "#45;MANAGER&#45;&gt;CMP&#45;MANAGER&#45;GROUNDING -->\n<g id="
    '"part_of:CMP&#45;MANAGER&#45;GROUNDING:CMP&#45;MANAGER" clas'
    's="edge">\n<title>CMP&#45;MANAGER&#45;&gt;CMP&#45;MANAGER&#45'
    ';GROUNDING</title>\n<path fill="none" stroke="#526677" stroke'
    '-width="1.5" d="M1487.24,-172.05C1478.95,-168.05 1470.41,-16'
    "4.45 1461.97,-161.68 1256.95,-94.43 1190.33,-151.67 979.97,-"
    '103.68 967.31,-100.79 954.22,-97.23 941.29,-93.33"/>\n</g>\n<!'
    '-- CMP&#45;MANAGER&#45;SCHED&#45;COMP -->\n<g id="CMP&#45;MAN'
    'AGER&#45;SCHED&#45;COMP" class="node">\n<title>CMP&#45;MANAGE'
    'R&#45;SCHED&#45;COMP</title>\n<path fill="#edf5fc" stroke="#2'
    'd6994" d="M1268.93,-103.68C1268.93,-103.68 1001.01,-103.68 1'
    "001.01,-103.68 995.01,-103.68 989.01,-97.68 989.01,-91.68 98"
    "9.01,-91.68 989.01,-12 989.01,-12 989.01,-6 995.01,0 1001.01"
    ",0 1001.01,0 1268.93,0 1268.93,0 1274.93,0 1280.93,-6 1280.9"
    "3,-12 1280.93,-12 1280.93,-91.68 1280.93,-91.68 1280.93,-97."
    '68 1274.93,-103.68 1268.93,-103.68"/>\n<text xml:space="prese'
    'rve" text-anchor="middle" x="1134.97" y="-78.84" font-family'
    '="Arial" font-size="18.00" fill="#21384b">Scheduling and</te'
    'xt>\n<text xml:space="preserve" text-anchor="middle" x="1134.'
    '97" y="-57.24" font-family="Arial" font-size="18.00" fill="#'
    '21384b">Completion</text>\n<text xml:space="preserve" text-an'
    'chor="middle" x="1134.97" y="-35.64" font-family="Arial" fon'
    't-size="18.00" fill="#21384b">CMP&#45;MANAGER&#45;SCHED&#45;'
    'COMP</text>\n<text xml:space="preserve" text-anchor="middle" '
    'x="1134.97" y="-14.04" font-family="Arial" font-size="18.00"'
    ' fill="#21384b">implemented</text>\n</g>\n<!-- CMP&#45;MANAGER'
    '&#45;&gt;CMP&#45;MANAGER&#45;SCHED&#45;COMP -->\n<g id="part_'
    'of:CMP&#45;MANAGER&#45;SCHED&#45;COMP:CMP&#45;MANAGER" class'
    '="edge">\n<title>CMP&#45;MANAGER&#45;&gt;CMP&#45;MANAGER&#45;'
    'SCHED&#45;COMP</title>\n<path fill="none" stroke="#526677" st'
    'roke-width="1.5" d="M1483.38,-172C1476.25,-168.32 1469.02,-1'
    "64.81 1461.97,-161.68 1452.83,-157.62 1363.98,-128.09 1281.2"
    ',-100.82"/>\n</g>\n<!-- CMP&#45;MEM&#45;EPISODIC -->\n<g id="CM'
    'P&#45;MEM&#45;EPISODIC" class="node">\n<title>CMP&#45;MEM&#45'
    ';EPISODIC</title>\n<path fill="#edf5fc" stroke="#2d6994" d="M'
    "1492.93,-92.88C1492.93,-92.88 1311.01,-92.88 1311.01,-92.88 "
    "1305.01,-92.88 1299.01,-86.88 1299.01,-80.88 1299.01,-80.88 "
    "1299.01,-22.8 1299.01,-22.8 1299.01,-16.8 1305.01,-10.8 1311"
    ".01,-10.8 1311.01,-10.8 1492.93,-10.8 1492.93,-10.8 1498.93,"
    "-10.8 1504.93,-16.8 1504.93,-22.8 1504.93,-22.8 1504.93,-80."
    "88 1504.93,-80.88 1504.93,-86.88 1498.93,-92.88 1492.93,-92."
    '88"/>\n<text xml:space="preserve" text-anchor="middle" x="140'
    '1.97" y="-68.04" font-family="Arial" font-size="18.00" fill='
    '"#21384b">Episodic Memory</text>\n<text xml:space="preserve" '
    'text-anchor="middle" x="1401.97" y="-46.44" font-family="Ari'
    'al" font-size="18.00" fill="#21384b">CMP&#45;MEM&#45;EPISODI'
    'C</text>\n<text xml:space="preserve" text-anchor="middle" x="'
    '1401.97" y="-24.84" font-family="Arial" font-size="18.00" fi'
    'll="#21384b">partial</text>\n</g>\n<!-- CMP&#45;MEM&#45;FACTS '
    '-->\n<g id="CMP&#45;MEM&#45;FACTS" class="node">\n<title>CMP&#'
    '45;MEM&#45;FACTS</title>\n<path fill="#edf5fc" stroke="#2d699'
    '4" d="M1689.42,-92.88C1689.42,-92.88 1534.52,-92.88 1534.52,'
    "-92.88 1528.52,-92.88 1522.52,-86.88 1522.52,-80.88 1522.52,"
    "-80.88 1522.52,-22.8 1522.52,-22.8 1522.52,-16.8 1528.52,-10"
    ".8 1534.52,-10.8 1534.52,-10.8 1689.42,-10.8 1689.42,-10.8 1"
    "695.42,-10.8 1701.42,-16.8 1701.42,-22.8 1701.42,-22.8 1701."
    "42,-80.88 1701.42,-80.88 1701.42,-86.88 1695.42,-92.88 1689."
    '42,-92.88"/>\n<text xml:space="preserve" text-anchor="middle"'
    ' x="1611.97" y="-68.04" font-family="Arial" font-size="18.00'
    '" fill="#21384b">Semantic Facts</text>\n<text xml:space="pres'
    'erve" text-anchor="middle" x="1611.97" y="-46.44" font-famil'
    'y="Arial" font-size="18.00" fill="#21384b">CMP&#45;MEM&#45;F'
    'ACTS</text>\n<text xml:space="preserve" text-anchor="middle" '
    'x="1611.97" y="-24.84" font-family="Arial" font-size="18.00"'
    ' fill="#21384b">implemented</text>\n</g>\n<!-- CMP&#45;MEM&#45'
    ';HYPOTHESES -->\n<g id="CMP&#45;MEM&#45;HYPOTHESES" class="no'
    'de">\n<title>CMP&#45;MEM&#45;HYPOTHESES</title>\n<path fill="#'
    'edf5fc" stroke="#2d6994" d="M1950.43,-92.88C1950.43,-92.88 1'
    "731.5,-92.88 1731.5,-92.88 1725.5,-92.88 1719.5,-86.88 1719."
    "5,-80.88 1719.5,-80.88 1719.5,-22.8 1719.5,-22.8 1719.5,-16."
    "8 1725.5,-10.8 1731.5,-10.8 1731.5,-10.8 1950.43,-10.8 1950."
    "43,-10.8 1956.43,-10.8 1962.43,-16.8 1962.43,-22.8 1962.43,-"
    "22.8 1962.43,-80.88 1962.43,-80.88 1962.43,-86.88 1956.43,-9"
    '2.88 1950.43,-92.88"/>\n<text xml:space="preserve" text-ancho'
    'r="middle" x="1840.97" y="-68.04" font-family="Arial" font-s'
    'ize="18.00" fill="#21384b">Hypotheses</text>\n<text xml:space'
    '="preserve" text-anchor="middle" x="1840.97" y="-46.44" font'
    '-family="Arial" font-size="18.00" fill="#21384b">CMP&#45;MEM'
    '&#45;HYPOTHESES</text>\n<text xml:space="preserve" text-ancho'
    'r="middle" x="1840.97" y="-24.84" font-family="Arial" font-s'
    'ize="18.00" fill="#21384b">partial</text>\n</g>\n<!-- CMP&#45;'
    'MEM&#45;RETRIEVAL -->\n<g id="CMP&#45;MEM&#45;RETRIEVAL" clas'
    's="node">\n<title>CMP&#45;MEM&#45;RETRIEVAL</title>\n<path fil'
    'l="#edf5fc" stroke="#2d6994" d="M1858.93,-254.56C1858.93,-25'
    "4.56 1663,-254.56 1663,-254.56 1657,-254.56 1651,-248.56 165"
    "1,-242.56 1651,-242.56 1651,-184.48 1651,-184.48 1651,-178.4"
    "8 1657,-172.48 1663,-172.48 1663,-172.48 1858.93,-172.48 185"
    "8.93,-172.48 1864.93,-172.48 1870.93,-178.48 1870.93,-184.48"
    " 1870.93,-184.48 1870.93,-242.56 1870.93,-242.56 1870.93,-24"
    '8.56 1864.93,-254.56 1858.93,-254.56"/>\n<text xml:space="pre'
    'serve" text-anchor="middle" x="1760.97" y="-229.72" font-fam'
    'ily="Arial" font-size="18.00" fill="#21384b">Memory Retrieva'
    'l</text>\n<text xml:space="preserve" text-anchor="middle" x="'
    '1760.97" y="-208.12" font-family="Arial" font-size="18.00" f'
    'ill="#21384b">CMP&#45;MEM&#45;RETRIEVAL</text>\n<text xml:spa'
    'ce="preserve" text-anchor="middle" x="1760.97" y="-186.52" f'
    'ont-family="Arial" font-size="18.00" fill="#21384b">partial<'
    '/text>\n</g>\n<!-- CMP&#45;MEM&#45;STRATEGY -->\n<g id="CMP&#45'
    ';MEM&#45;STRATEGY" class="node">\n<title>CMP&#45;MEM&#45;STRA'
    'TEGY</title>\n<path fill="#edf5fc" stroke="#2d6994" d="M2185.'
    "43,-103.68C2185.43,-103.68 1992.51,-103.68 1992.51,-103.68 1"
    "986.51,-103.68 1980.51,-97.68 1980.51,-91.68 1980.51,-91.68 "
    "1980.51,-12 1980.51,-12 1980.51,-6 1986.51,0 1992.51,0 1992."
    "51,0 2185.43,0 2185.43,0 2191.43,0 2197.43,-6 2197.43,-12 21"
    "97.43,-12 2197.43,-91.68 2197.43,-91.68 2197.43,-97.68 2191."
    '43,-103.68 2185.43,-103.68"/>\n<text xml:space="preserve" tex'
    't-anchor="middle" x="2088.97" y="-78.84" font-family="Arial"'
    ' font-size="18.00" fill="#21384b">Strategy / Experiment</tex'
    't>\n<text xml:space="preserve" text-anchor="middle" x="2088.9'
    '7" y="-57.24" font-family="Arial" font-size="18.00" fill="#2'
    '1384b">Memory</text>\n<text xml:space="preserve" text-anchor='
    '"middle" x="2088.97" y="-35.64" font-family="Arial" font-siz'
    'e="18.00" fill="#21384b">CMP&#45;MEM&#45;STRATEGY</text>\n<te'
    'xt xml:space="preserve" text-anchor="middle" x="2088.97" y="'
    '-14.04" font-family="Arial" font-size="18.00" fill="#21384b"'
    ">implemented</text>\n</g>\n<!-- CMP&#45;MEM&#45;TOPOLOGY -->\n<"
    'g id="CMP&#45;MEM&#45;TOPOLOGY" class="node">\n<title>CMP&#45'
    ';MEM&#45;TOPOLOGY</title>\n<path fill="#edf5fc" stroke="#2d69'
    '94" d="M2424.43,-92.88C2424.43,-92.88 2227.51,-92.88 2227.51'
    ",-92.88 2221.51,-92.88 2215.51,-86.88 2215.51,-80.88 2215.51"
    ",-80.88 2215.51,-22.8 2215.51,-22.8 2215.51,-16.8 2221.51,-1"
    "0.8 2227.51,-10.8 2227.51,-10.8 2424.43,-10.8 2424.43,-10.8 "
    "2430.43,-10.8 2436.43,-16.8 2436.43,-22.8 2436.43,-22.8 2436"
    ".43,-80.88 2436.43,-80.88 2436.43,-86.88 2430.43,-92.88 2424"
    '.43,-92.88"/>\n<text xml:space="preserve" text-anchor="middle'
    '" x="2325.97" y="-68.04" font-family="Arial" font-size="18.0'
    '0" fill="#21384b">Topological Memory</text>\n<text xml:space='
    '"preserve" text-anchor="middle" x="2325.97" y="-46.44" font-'
    'family="Arial" font-size="18.00" fill="#21384b">CMP&#45;MEM&'
    '#45;TOPOLOGY</text>\n<text xml:space="preserve" text-anchor="'
    'middle" x="2325.97" y="-24.84" font-family="Arial" font-size'
    '="18.00" fill="#21384b">implemented</text>\n</g>\n<!-- CMP&#45'
    ';MEMORY -->\n<g id="CMP&#45;MEMORY" class="node">\n<title>CMP&'
    '#45;MEMORY</title>\n<path fill="#edf5fc" stroke="#2d6994" d="'
    "M2029.43,-254.56C2029.43,-254.56 1900.51,-254.56 1900.51,-25"
    "4.56 1894.51,-254.56 1888.51,-248.56 1888.51,-242.56 1888.51"
    ",-242.56 1888.51,-184.48 1888.51,-184.48 1888.51,-178.48 189"
    "4.51,-172.48 1900.51,-172.48 1900.51,-172.48 2029.43,-172.48"
    " 2029.43,-172.48 2035.43,-172.48 2041.43,-178.48 2041.43,-18"
    "4.48 2041.43,-184.48 2041.43,-242.56 2041.43,-242.56 2041.43"
    ',-248.56 2035.43,-254.56 2029.43,-254.56"/>\n<text xml:space='
    '"preserve" text-anchor="middle" x="1964.97" y="-229.72" font'
    '-family="Arial" font-size="18.00" fill="#21384b">Memory</tex'
    't>\n<text xml:space="preserve" text-anchor="middle" x="1964.9'
    '7" y="-208.12" font-family="Arial" font-size="18.00" fill="#'
    '21384b">CMP&#45;MEMORY</text>\n<text xml:space="preserve" tex'
    't-anchor="middle" x="1964.97" y="-186.52" font-family="Arial'
    '" font-size="18.00" fill="#21384b">partial</text>\n</g>\n<!-- '
    'CMP&#45;MEMORY&#45;&gt;CMP&#45;MEM&#45;EPISODIC -->\n<g id="p'
    'art_of:CMP&#45;MEM&#45;EPISODIC:CMP&#45;MEMORY" class="edge"'
    ">\n<title>CMP&#45;MEMORY&#45;&gt;CMP&#45;MEM&#45;EPISODIC</ti"
    'tle>\n<path fill="none" stroke="#526677" stroke-width="1.5" d'
    '="M1903.65,-172.19C1895.89,-168.19 1887.89,-164.55 1879.97,-'
    "161.68 1725.15,-105.5 1671.71,-151.03 1513.97,-103.68 1504.2"
    '5,-100.76 1494.29,-97.18 1484.5,-93.28"/>\n</g>\n<!-- CMP&#45;'
    'MEMORY&#45;&gt;CMP&#45;MEM&#45;FACTS -->\n<g id="part_of:CMP&'
    '#45;MEM&#45;FACTS:CMP&#45;MEMORY" class="edge">\n<title>CMP&#'
    '45;MEMORY&#45;&gt;CMP&#45;MEM&#45;FACTS</title>\n<path fill="'
    'none" stroke="#526677" stroke-width="1.5" d="M1900.76,-172.2'
    "3C1893.85,-168.46 1886.83,-164.87 1879.97,-161.68 1807.95,-1"
    "28.23 1784.03,-134.79 1710.97,-103.68 1703.5,-100.5 1695.82,"
    '-97 1688.2,-93.36"/>\n</g>\n<!-- CMP&#45;MEMORY&#45;&gt;CMP&#4'
    '5;MEM&#45;HYPOTHESES -->\n<g id="part_of:CMP&#45;MEM&#45;HYPO'
    'THESES:CMP&#45;MEMORY" class="edge">\n<title>CMP&#45;MEMORY&#'
    '45;&gt;CMP&#45;MEM&#45;HYPOTHESES</title>\n<path fill="none" '
    'stroke="#526677" stroke-width="1.5" d="M1933.68,-172.23C1914'
    '.88,-148.02 1891.05,-117.33 1872.25,-93.12"/>\n</g>\n<!-- CMP&'
    '#45;MEMORY&#45;&gt;CMP&#45;MEM&#45;STRATEGY -->\n<g id="part_'
    'of:CMP&#45;MEM&#45;STRATEGY:CMP&#45;MEMORY" class="edge">\n<t'
    "itle>CMP&#45;MEMORY&#45;&gt;CMP&#45;MEM&#45;STRATEGY</title>"
    '\n<path fill="none" stroke="#526677" stroke-width="1.5" d="M1'
    "996.26,-172.23C2012.33,-151.53 2032.08,-126.09 2049.22,-104."
    '02"/>\n</g>\n<!-- CMP&#45;MEMORY&#45;&gt;CMP&#45;MEM&#45;TOPOL'
    'OGY -->\n<g id="part_of:CMP&#45;MEM&#45;TOPOLOGY:CMP&#45;MEMO'
    'RY" class="edge">\n<title>CMP&#45;MEMORY&#45;&gt;CMP&#45;MEM&'
    '#45;TOPOLOGY</title>\n<path fill="none" stroke="#526677" stro'
    'ke-width="1.5" d="M2030.53,-172.18C2037.35,-168.47 2044.24,-'
    "164.9 2050.97,-161.68 2117.33,-129.95 2137.65,-130.92 2205.9"
    '7,-103.68 2214.27,-100.37 2222.87,-96.87 2231.47,-93.32"/>\n<'
    '/g>\n<!-- CMP&#45;SKILL&#45;COMPETENCE -->\n<g id="CMP&#45;SKI'
    'LL&#45;COMPETENCE" class="node">\n<title>CMP&#45;SKILL&#45;CO'
    'MPETENCE</title>\n<path fill="#edf5fc" stroke="#2d6994" d="M2'
    "695.95,-103.68C2695.95,-103.68 2465.99,-103.68 2465.99,-103."
    "68 2459.99,-103.68 2453.99,-97.68 2453.99,-91.68 2453.99,-91"
    ".68 2453.99,-12 2453.99,-12 2453.99,-6 2459.99,0 2465.99,0 2"
    "465.99,0 2695.95,0 2695.95,0 2701.95,0 2707.95,-6 2707.95,-1"
    "2 2707.95,-12 2707.95,-91.68 2707.95,-91.68 2707.95,-97.68 2"
    '701.95,-103.68 2695.95,-103.68"/>\n<text xml:space="preserve"'
    ' text-anchor="middle" x="2580.97" y="-78.84" font-family="Ar'
    'ial" font-size="18.00" fill="#21384b">Skill Competence</text'
    '>\n<text xml:space="preserve" text-anchor="middle" x="2580.97'
    '" y="-57.24" font-family="Arial" font-size="18.00" fill="#21'
    '384b">Registry</text>\n<text xml:space="preserve" text-anchor'
    '="middle" x="2580.97" y="-35.64" font-family="Arial" font-si'
    'ze="18.00" fill="#21384b">CMP&#45;SKILL&#45;COMPETENCE</text'
    '>\n<text xml:space="preserve" text-anchor="middle" x="2580.97'
    '" y="-14.04" font-family="Arial" font-size="18.00" fill="#21'
    '384b">partial</text>\n</g>\n<!-- CMP&#45;MEMORY&#45;&gt;CMP&#4'
    '5;SKILL&#45;COMPETENCE -->\n<g id="part_of:CMP&#45;SKILL&#45;'
    'COMPETENCE:CMP&#45;MEMORY" class="edge">\n<title>CMP&#45;MEMO'
    'RY&#45;&gt;CMP&#45;SKILL&#45;COMPETENCE</title>\n<path fill="'
    'none" stroke="#526677" stroke-width="1.5" d="M2027.01,-172.1'
    "1C2034.86,-168.13 2042.96,-164.51 2050.97,-161.68 2217.83,-1"
    "02.65 2273.56,-147.8 2444.97,-103.68 2447.9,-102.93 2450.85,"
    '-102.13 2453.82,-101.3"/>\n</g>\n<!-- CMP&#45;NO&#45;SPOILER&#'
    '45;FIREWALL -->\n<g id="CMP&#45;NO&#45;SPOILER&#45;FIREWALL" '
    'class="node">\n<title>CMP&#45;NO&#45;SPOILER&#45;FIREWALL</ti'
    'tle>\n<path fill="#edf5fc" stroke="#2d6994" d="M2326.44,-254.'
    "56C2326.44,-254.56 2071.5,-254.56 2071.5,-254.56 2065.5,-254"
    ".56 2059.5,-248.56 2059.5,-242.56 2059.5,-242.56 2059.5,-184"
    ".48 2059.5,-184.48 2059.5,-178.48 2065.5,-172.48 2071.5,-172"
    ".48 2071.5,-172.48 2326.44,-172.48 2326.44,-172.48 2332.44,-"
    "172.48 2338.44,-178.48 2338.44,-184.48 2338.44,-184.48 2338."
    "44,-242.56 2338.44,-242.56 2338.44,-248.56 2332.44,-254.56 2"
    '326.44,-254.56"/>\n<text xml:space="preserve" text-anchor="mi'
    'ddle" x="2198.97" y="-229.72" font-family="Arial" font-size='
    '"18.00" fill="#21384b">No&#45;Spoiler Firewall</text>\n<text '
    'xml:space="preserve" text-anchor="middle" x="2198.97" y="-20'
    '8.12" font-family="Arial" font-size="18.00" fill="#21384b">C'
    'MP&#45;NO&#45;SPOILER&#45;FIREWALL</text>\n<text xml:space="p'
    'reserve" text-anchor="middle" x="2198.97" y="-186.52" font-f'
    'amily="Arial" font-size="18.00" fill="#21384b">implemented</'
    'text>\n</g>\n<!-- CMP&#45;OBSERVATION&#45;BUILDER -->\n<g id="C'
    'MP&#45;OBSERVATION&#45;BUILDER" class="node">\n<title>CMP&#45'
    ';OBSERVATION&#45;BUILDER</title>\n<path fill="#edf5fc" stroke'
    '="#2d6994" d="M2999.95,-92.88C2999.95,-92.88 2737.99,-92.88 '
    "2737.99,-92.88 2731.99,-92.88 2725.99,-86.88 2725.99,-80.88 "
    "2725.99,-80.88 2725.99,-22.8 2725.99,-22.8 2725.99,-16.8 273"
    "1.99,-10.8 2737.99,-10.8 2737.99,-10.8 2999.95,-10.8 2999.95"
    ",-10.8 3005.95,-10.8 3011.95,-16.8 3011.95,-22.8 3011.95,-22"
    ".8 3011.95,-80.88 3011.95,-80.88 3011.95,-86.88 3005.95,-92."
    '88 2999.95,-92.88"/>\n<text xml:space="preserve" text-anchor='
    '"middle" x="2868.97" y="-68.04" font-family="Arial" font-siz'
    'e="18.00" fill="#21384b">Observation Builder</text>\n<text xm'
    'l:space="preserve" text-anchor="middle" x="2868.97" y="-46.4'
    '4" font-family="Arial" font-size="18.00" fill="#21384b">CMP&'
    '#45;OBSERVATION&#45;BUILDER</text>\n<text xml:space="preserve'
    '" text-anchor="middle" x="2868.97" y="-24.84" font-family="A'
    'rial" font-size="18.00" fill="#21384b">implemented</text>\n</'
    'g>\n<!-- CMP&#45;PERCEPTION -->\n<g id="CMP&#45;PERCEPTION" cl'
    'ass="node">\n<title>CMP&#45;PERCEPTION</title>\n<path fill="#e'
    'df5fc" stroke="#2d6994" d="M2533.43,-254.56C2533.43,-254.56 '
    "2368.5,-254.56 2368.5,-254.56 2362.5,-254.56 2356.5,-248.56 "
    "2356.5,-242.56 2356.5,-242.56 2356.5,-184.48 2356.5,-184.48 "
    "2356.5,-178.48 2362.5,-172.48 2368.5,-172.48 2368.5,-172.48 "
    "2533.43,-172.48 2533.43,-172.48 2539.43,-172.48 2545.43,-178"
    ".48 2545.43,-184.48 2545.43,-184.48 2545.43,-242.56 2545.43,"
    '-242.56 2545.43,-248.56 2539.43,-254.56 2533.43,-254.56"/>\n<'
    'text xml:space="preserve" text-anchor="middle" x="2450.97" y'
    '="-229.72" font-family="Arial" font-size="18.00" fill="#2138'
    '4b">Perception</text>\n<text xml:space="preserve" text-anchor'
    '="middle" x="2450.97" y="-208.12" font-family="Arial" font-s'
    'ize="18.00" fill="#21384b">CMP&#45;PERCEPTION</text>\n<text x'
    'ml:space="preserve" text-anchor="middle" x="2450.97" y="-186'
    '.52" font-family="Arial" font-size="18.00" fill="#21384b">pa'
    "rtial</text>\n</g>\n<!-- CMP&#45;PERCEPTION&#45;&gt;CMP&#45;OB"
    'SERVATION&#45;BUILDER -->\n<g id="part_of:CMP&#45;OBSERVATION'
    '&#45;BUILDER:CMP&#45;PERCEPTION" class="edge">\n<title>CMP&#4'
    "5;PERCEPTION&#45;&gt;CMP&#45;OBSERVATION&#45;BUILDER</title>"
    '\n<path fill="none" stroke="#526677" stroke-width="1.5" d="M2'
    "531.44,-172C2539.33,-168.38 2547.27,-164.88 2554.97,-161.68 "
    '2573.98,-153.77 2669.42,-120.84 2750.15,-93.25"/>\n</g>\n<!-- '
    'CMP&#45;PERCEPTION&#45;UI&#45;STATE -->\n<g id="CMP&#45;PERCE'
    'PTION&#45;UI&#45;STATE" class="node">\n<title>CMP&#45;PERCEPT'
    'ION&#45;UI&#45;STATE</title>\n<path fill="#edf5fc" stroke="#2'
    'd6994" d="M3294.43,-92.88C3294.43,-92.88 3041.51,-92.88 3041'
    ".51,-92.88 3035.51,-92.88 3029.51,-86.88 3029.51,-80.88 3029"
    ".51,-80.88 3029.51,-22.8 3029.51,-22.8 3029.51,-16.8 3035.51"
    ",-10.8 3041.51,-10.8 3041.51,-10.8 3294.43,-10.8 3294.43,-10"
    ".8 3300.43,-10.8 3306.43,-16.8 3306.43,-22.8 3306.43,-22.8 3"
    "306.43,-80.88 3306.43,-80.88 3306.43,-86.88 3300.43,-92.88 3"
    '294.43,-92.88"/>\n<text xml:space="preserve" text-anchor="mid'
    'dle" x="3167.97" y="-68.04" font-family="Arial" font-size="1'
    '8.00" fill="#21384b">UI State Classification</text>\n<text xm'
    'l:space="preserve" text-anchor="middle" x="3167.97" y="-46.4'
    '4" font-family="Arial" font-size="18.00" fill="#21384b">CMP&'
    '#45;PERCEPTION&#45;UI&#45;STATE</text>\n<text xml:space="pres'
    'erve" text-anchor="middle" x="3167.97" y="-24.84" font-famil'
    'y="Arial" font-size="18.00" fill="#21384b">implemented</text'
    ">\n</g>\n<!-- CMP&#45;PERCEPTION&#45;&gt;CMP&#45;PERCEPTION&#4"
    '5;UI&#45;STATE -->\n<g id="part_of:CMP&#45;PERCEPTION&#45;UI&'
    '#45;STATE:CMP&#45;PERCEPTION" class="edge">\n<title>CMP&#45;P'
    "ERCEPTION&#45;&gt;CMP&#45;PERCEPTION&#45;UI&#45;STATE</title"
    '>\n<path fill="none" stroke="#526677" stroke-width="1.5" d="M'
    "2526.48,-172.06C2535.9,-168.09 2545.53,-164.49 2554.97,-161."
    "68 2755.01,-102.15 2817.68,-150.94 3020.97,-103.68 3033.46,-"
    '100.78 3046.38,-97.2 3059.14,-93.3"/>\n</g>\n<!-- CMP&#45;REPL'
    'AY&#45;BUFFER -->\n<g id="CMP&#45;REPLAY&#45;BUFFER" class="n'
    'ode">\n<title>CMP&#45;REPLAY&#45;BUFFER</title>\n<path fill="#'
    'edf5fc" stroke="#2d6994" d="M2772.44,-254.56C2772.44,-254.56'
    " 2575.5,-254.56 2575.5,-254.56 2569.5,-254.56 2563.5,-248.56"
    " 2563.5,-242.56 2563.5,-242.56 2563.5,-184.48 2563.5,-184.48"
    " 2563.5,-178.48 2569.5,-172.48 2575.5,-172.48 2575.5,-172.48"
    " 2772.44,-172.48 2772.44,-172.48 2778.44,-172.48 2784.44,-17"
    "8.48 2784.44,-184.48 2784.44,-184.48 2784.44,-242.56 2784.44"
    ',-242.56 2784.44,-248.56 2778.44,-254.56 2772.44,-254.56"/>\n'
    '<text xml:space="preserve" text-anchor="middle" x="2673.97" '
    'y="-229.72" font-family="Arial" font-size="18.00" fill="#213'
    '84b">Replay Buffer</text>\n<text xml:space="preserve" text-an'
    'chor="middle" x="2673.97" y="-208.12" font-family="Arial" fo'
    'nt-size="18.00" fill="#21384b">CMP&#45;REPLAY&#45;BUFFER</te'
    'xt>\n<text xml:space="preserve" text-anchor="middle" x="2673.'
    '97" y="-186.52" font-family="Arial" font-size="18.00" fill="'
    '#21384b">partial</text>\n</g>\n<!-- CMP&#45;SAFETY&#45;FILTER '
    '-->\n<g id="CMP&#45;SAFETY&#45;FILTER" class="node">\n<title>C'
    'MP&#45;SAFETY&#45;FILTER</title>\n<path fill="#edf5fc" stroke'
    '="#2d6994" d="M2999.93,-254.56C2999.93,-254.56 2814.01,-254.'
    "56 2814.01,-254.56 2808.01,-254.56 2802.01,-248.56 2802.01,-"
    "242.56 2802.01,-242.56 2802.01,-184.48 2802.01,-184.48 2802."
    "01,-178.48 2808.01,-172.48 2814.01,-172.48 2814.01,-172.48 2"
    "999.93,-172.48 2999.93,-172.48 3005.93,-172.48 3011.93,-178."
    "48 3011.93,-184.48 3011.93,-184.48 3011.93,-242.56 3011.93,-"
    '242.56 3011.93,-248.56 3005.93,-254.56 2999.93,-254.56"/>\n<t'
    'ext xml:space="preserve" text-anchor="middle" x="2906.97" y='
    '"-229.72" font-family="Arial" font-size="18.00" fill="#21384'
    'b">SafetyFilter</text>\n<text xml:space="preserve" text-ancho'
    'r="middle" x="2906.97" y="-208.12" font-family="Arial" font-'
    'size="18.00" fill="#21384b">CMP&#45;SAFETY&#45;FILTER</text>'
    '\n<text xml:space="preserve" text-anchor="middle" x="2906.97"'
    ' y="-186.52" font-family="Arial" font-size="18.00" fill="#21'
    '384b">partial</text>\n</g>\n<!-- CMP&#45;SCREEN&#45;CAPTURE --'
    '>\n<g id="CMP&#45;SCREEN&#45;CAPTURE" class="node">\n<title>CM'
    'P&#45;SCREEN&#45;CAPTURE</title>\n<path fill="#edf5fc" stroke'
    '="#2d6994" d="M3256.44,-254.56C3256.44,-254.56 3041.5,-254.5'
    "6 3041.5,-254.56 3035.5,-254.56 3029.5,-248.56 3029.5,-242.5"
    "6 3029.5,-242.56 3029.5,-184.48 3029.5,-184.48 3029.5,-178.4"
    "8 3035.5,-172.48 3041.5,-172.48 3041.5,-172.48 3256.44,-172."
    "48 3256.44,-172.48 3262.44,-172.48 3268.44,-178.48 3268.44,-"
    "184.48 3268.44,-184.48 3268.44,-242.56 3268.44,-242.56 3268."
    '44,-248.56 3262.44,-254.56 3256.44,-254.56"/>\n<text xml:spac'
    'e="preserve" text-anchor="middle" x="3148.97" y="-229.72" fo'
    'nt-family="Arial" font-size="18.00" fill="#21384b">Screen Ca'
    'pture</text>\n<text xml:space="preserve" text-anchor="middle"'
    ' x="3148.97" y="-208.12" font-family="Arial" font-size="18.0'
    '0" fill="#21384b">CMP&#45;SCREEN&#45;CAPTURE</text>\n<text xm'
    'l:space="preserve" text-anchor="middle" x="3148.97" y="-186.'
    '52" font-family="Arial" font-size="18.00" fill="#21384b">imp'
    "lemented</text>\n</g>\n<!-- CMP&#45;SKILL&#45;TRAINER -->\n<g i"
    'd="CMP&#45;SKILL&#45;TRAINER" class="node">\n<title>CMP&#45;S'
    'KILL&#45;TRAINER</title>\n<path fill="#edf5fc" stroke="#2d699'
    '4" d="M3479.94,-254.56C3479.94,-254.56 3298,-254.56 3298,-25'
    "4.56 3292,-254.56 3286,-248.56 3286,-242.56 3286,-242.56 328"
    "6,-184.48 3286,-184.48 3286,-178.48 3292,-172.48 3298,-172.4"
    "8 3298,-172.48 3479.94,-172.48 3479.94,-172.48 3485.94,-172."
    "48 3491.94,-178.48 3491.94,-184.48 3491.94,-184.48 3491.94,-"
    "242.56 3491.94,-242.56 3491.94,-248.56 3485.94,-254.56 3479."
    '94,-254.56"/>\n<text xml:space="preserve" text-anchor="middle'
    '" x="3388.97" y="-229.72" font-family="Arial" font-size="18.'
    '00" fill="#21384b">SkillTrainer</text>\n<text xml:space="pres'
    'erve" text-anchor="middle" x="3388.97" y="-208.12" font-fami'
    'ly="Arial" font-size="18.00" fill="#21384b">CMP&#45;SKILL&#4'
    '5;TRAINER</text>\n<text xml:space="preserve" text-anchor="mid'
    'dle" x="3388.97" y="-186.52" font-family="Arial" font-size="'
    '18.00" fill="#21384b">target&#45;only</text>\n</g>\n<!-- CMP&#'
    '45;TEMPORAL&#45;STATE -->\n<g id="CMP&#45;TEMPORAL&#45;STATE"'
    ' class="node">\n<title>CMP&#45;TEMPORAL&#45;STATE</title>\n<pa'
    'th fill="#edf5fc" stroke="#2d6994" d="M3732.44,-254.56C3732.'
    "44,-254.56 3521.5,-254.56 3521.5,-254.56 3515.5,-254.56 3509"
    ".5,-248.56 3509.5,-242.56 3509.5,-242.56 3509.5,-184.48 3509"
    ".5,-184.48 3509.5,-178.48 3515.5,-172.48 3521.5,-172.48 3521"
    ".5,-172.48 3732.44,-172.48 3732.44,-172.48 3738.44,-172.48 3"
    "744.44,-178.48 3744.44,-184.48 3744.44,-184.48 3744.44,-242."
    "56 3744.44,-242.56 3744.44,-248.56 3738.44,-254.56 3732.44,-"
    '254.56"/>\n<text xml:space="preserve" text-anchor="middle" x='
    '"3626.97" y="-229.72" font-family="Arial" font-size="18.00" '
    'fill="#21384b">Temporal State</text>\n<text xml:space="preser'
    've" text-anchor="middle" x="3626.97" y="-208.12" font-family'
    '="Arial" font-size="18.00" fill="#21384b">CMP&#45;TEMPORAL&#'
    '45;STATE</text>\n<text xml:space="preserve" text-anchor="midd'
    'le" x="3626.97" y="-186.52" font-family="Arial" font-size="1'
    '8.00" fill="#21384b">target&#45;only</text>\n</g>\n<!-- CMP&#4'
    '5;VISIBLE&#45;STATE&#45;BRIDGE -->\n<g id="CMP&#45;VISIBLE&#4'
    '5;STATE&#45;BRIDGE" class="node">\n<title>CMP&#45;VISIBLE&#45'
    ';STATE&#45;BRIDGE</title>\n<path fill="#edf5fc" stroke="#2d69'
    '94" d="M4029.45,-265.36C4029.45,-265.36 3774.49,-265.36 3774'
    ".49,-265.36 3768.49,-265.36 3762.49,-259.36 3762.49,-253.36 "
    "3762.49,-253.36 3762.49,-173.68 3762.49,-173.68 3762.49,-167"
    ".68 3768.49,-161.68 3774.49,-161.68 3774.49,-161.68 4029.45,"
    "-161.68 4029.45,-161.68 4035.45,-161.68 4041.45,-167.68 4041"
    ".45,-173.68 4041.45,-173.68 4041.45,-253.36 4041.45,-253.36 "
    '4041.45,-259.36 4035.45,-265.36 4029.45,-265.36"/>\n<text xml'
    ':space="preserve" text-anchor="middle" x="3901.97" y="-240.5'
    '2" font-family="Arial" font-size="18.00" fill="#21384b">Opti'
    'onal Visible&#45;State</text>\n<text xml:space="preserve" tex'
    't-anchor="middle" x="3901.97" y="-218.92" font-family="Arial'
    '" font-size="18.00" fill="#21384b">Bridge</text>\n<text xml:s'
    'pace="preserve" text-anchor="middle" x="3901.97" y="-197.32"'
    ' font-family="Arial" font-size="18.00" fill="#21384b">CMP&#4'
    '5;VISIBLE&#45;STATE&#45;BRIDGE</text>\n<text xml:space="prese'
    'rve" text-anchor="middle" x="3901.97" y="-175.72" font-famil'
    'y="Arial" font-size="18.00" fill="#21384b">implemented</text'
    '>\n</g>\n<!-- SYS&#45;AGA -->\n<g id="SYS&#45;AGA" class="node"'
    '>\n<title>SYS&#45;AGA</title>\n<path fill="#edf5fc" stroke="#2'
    'd6994" d="M2069.49,-427.04C2069.49,-427.04 1860.45,-427.04 1'
    "860.45,-427.04 1854.45,-427.04 1848.45,-421.04 1848.45,-415."
    "04 1848.45,-415.04 1848.45,-335.36 1848.45,-335.36 1848.45,-"
    "329.36 1854.45,-323.36 1860.45,-323.36 1860.45,-323.36 2069."
    "49,-323.36 2069.49,-323.36 2075.49,-323.36 2081.49,-329.36 2"
    "081.49,-335.36 2081.49,-335.36 2081.49,-415.04 2081.49,-415."
    '04 2081.49,-421.04 2075.49,-427.04 2069.49,-427.04"/>\n<text '
    'xml:space="preserve" text-anchor="middle" x="1964.97" y="-40'
    '2.2" font-family="Arial" font-size="18.00" fill="#21384b">Au'
    'tonomous Game Agent</text>\n<text xml:space="preserve" text-a'
    'nchor="middle" x="1964.97" y="-380.6" font-family="Arial" fo'
    'nt-size="18.00" fill="#21384b">Experiment System</text>\n<tex'
    't xml:space="preserve" text-anchor="middle" x="1964.97" y="-'
    '359" font-family="Arial" font-size="18.00" fill="#21384b">SY'
    'S&#45;AGA</text>\n<text xml:space="preserve" text-anchor="mid'
    'dle" x="1964.97" y="-337.4" font-family="Arial" font-size="1'
    '8.00" fill="#21384b">target&#45;only</text>\n</g>\n<!-- SYS&#4'
    '5;AGA&#45;&gt;CMP&#45;BODY -->\n<g id="part_of:CMP&#45;BODY:S'
    'YS&#45;AGA" class="edge">\n<title>SYS&#45;AGA&#45;&gt;CMP&#45'
    ';BODY</title>\n<path fill="none" stroke="#526677" stroke-widt'
    'h="1.5" d="M1848.18,-370.65C1478.42,-358.89 348.61,-318.96 1'
    '92.97,-265.36 185.31,-262.72 177.7,-259.06 170.45,-254.89"/>'
    "\n</g>\n<!-- SYS&#45;AGA&#45;&gt;CMP&#45;BODY&#45;CERTIFICATIO"
    'N -->\n<g id="part_of:CMP&#45;BODY&#45;CERTIFICATION:SYS&#45;'
    'AGA" class="edge">\n<title>SYS&#45;AGA&#45;&gt;CMP&#45;BODY&#'
    '45;CERTIFICATION</title>\n<path fill="none" stroke="#526677" '
    'stroke-width="1.5" d="M1848.19,-369.7C1545.19,-357.39 739.27'
    ",-320.32 477.97,-265.36 474.88,-264.71 471.76,-264.01 468.62"
    ',-263.26"/>\n</g>\n<!-- SYS&#45;AGA&#45;&gt;CMP&#45;CORTEX -->'
    '\n<g id="part_of:CMP&#45;CORTEX:SYS&#45;AGA" class="edge">\n<t'
    'itle>SYS&#45;AGA&#45;&gt;CMP&#45;CORTEX</title>\n<path fill="'
    'none" stroke="#526677" stroke-width="1.5" d="M1848.19,-371.5'
    "9C1568.02,-364.21 864.46,-338.73 641.97,-265.36 633.86,-262."
    '68 625.72,-259.06 617.9,-254.96"/>\n</g>\n<!-- SYS&#45;AGA&#45'
    ';&gt;CMP&#45;EVIDENCE&#45;LEDGER -->\n<g id="part_of:CMP&#45;'
    'EVIDENCE&#45;LEDGER:SYS&#45;AGA" class="edge">\n<title>SYS&#4'
    "5;AGA&#45;&gt;CMP&#45;EVIDENCE&#45;LEDGER</title>\n<path fill"
    '="none" stroke="#526677" stroke-width="1.5" d="M1848.26,-372'
    ".39C1651.03,-367.09 1240.39,-346.34 903.97,-265.36 892.35,-2"
    '62.56 880.38,-258.97 868.61,-255"/>\n</g>\n<!-- SYS&#45;AGA&#4'
    '5;&gt;CMP&#45;INDEPENDENT&#45;VERIFIER -->\n<g id="part_of:CM'
    'P&#45;INDEPENDENT&#45;VERIFIER:SYS&#45;AGA" class="edge">\n<t'
    "itle>SYS&#45;AGA&#45;&gt;CMP&#45;INDEPENDENT&#45;VERIFIER</t"
    'itle>\n<path fill="none" stroke="#526677" stroke-width="1.5" '
    'd="M1848.01,-363.71C1698.93,-348.88 1433.92,-317.61 1211.97,'
    '-265.36 1199.36,-262.39 1186.31,-258.85 1173.39,-255.03"/>\n<'
    "/g>\n<!-- SYS&#45;AGA&#45;&gt;CMP&#45;INPUT&#45;EXECUTOR -->\n"
    '<g id="part_of:CMP&#45;INPUT&#45;EXECUTOR:SYS&#45;AGA" class'
    '="edge">\n<title>SYS&#45;AGA&#45;&gt;CMP&#45;INPUT&#45;EXECUT'
    'OR</title>\n<path fill="none" stroke="#526677" stroke-width="'
    '1.5" d="M1848.13,-354.85C1745.23,-336.41 1591.94,-305.52 146'
    "1.97,-265.36 1452.01,-262.28 1441.73,-258.74 1431.56,-254.98"
    '"/>\n</g>\n<!-- SYS&#45;AGA&#45;&gt;CMP&#45;MANAGER -->\n<g id='
    '"part_of:CMP&#45;MANAGER:SYS&#45;AGA" class="edge">\n<title>S'
    'YS&#45;AGA&#45;&gt;CMP&#45;MANAGER</title>\n<path fill="none"'
    ' stroke="#526677" stroke-width="1.5" d="M1848.21,-340.72C178'
    "5.91,-321.4 1708.57,-295.07 1641.97,-265.36 1634.92,-262.22 "
    '1627.7,-258.69 1620.57,-255.01"/>\n</g>\n<!-- SYS&#45;AGA&#45;'
    '&gt;CMP&#45;MEM&#45;RETRIEVAL -->\n<g id="part_of:CMP&#45;MEM'
    '&#45;RETRIEVAL:SYS&#45;AGA" class="edge">\n<title>SYS&#45;AGA'
    '&#45;&gt;CMP&#45;MEM&#45;RETRIEVAL</title>\n<path fill="none"'
    ' stroke="#526677" stroke-width="1.5" d="M1899.58,-323.02C187'
    '1.49,-301.03 1839.14,-275.71 1812.75,-255.05"/>\n</g>\n<!-- SY'
    'S&#45;AGA&#45;&gt;CMP&#45;MEMORY -->\n<g id="part_of:CMP&#45;'
    'MEMORY:SYS&#45;AGA" class="edge">\n<title>SYS&#45;AGA&#45;&gt'
    ';CMP&#45;MEMORY</title>\n<path fill="none" stroke="#526677" s'
    'troke-width="1.5" d="M1964.97,-323.24C1964.97,-301.15 1964.9'
    '7,-275.65 1964.97,-254.91"/>\n</g>\n<!-- SYS&#45;AGA&#45;&gt;C'
    'MP&#45;NO&#45;SPOILER&#45;FIREWALL -->\n<g id="part_of:CMP&#4'
    '5;NO&#45;SPOILER&#45;FIREWALL:SYS&#45;AGA" class="edge">\n<ti'
    "tle>SYS&#45;AGA&#45;&gt;CMP&#45;NO&#45;SPOILER&#45;FIREWALL<"
    '/title>\n<path fill="none" stroke="#526677" stroke-width="1.5'
    '" d="M2039.97,-323.02C2072.19,-301.03 2109.31,-275.71 2139.5'
    '7,-255.05"/>\n</g>\n<!-- SYS&#45;AGA&#45;&gt;CMP&#45;PERCEPTIO'
    'N -->\n<g id="part_of:CMP&#45;PERCEPTION:SYS&#45;AGA" class="'
    'edge">\n<title>SYS&#45;AGA&#45;&gt;CMP&#45;PERCEPTION</title>'
    '\n<path fill="none" stroke="#526677" stroke-width="1.5" d="M2'
    "081.63,-346.68C2158.19,-327.24 2259.88,-298.75 2346.97,-265."
    '36 2355.13,-262.23 2363.52,-258.7 2371.83,-254.99"/>\n</g>\n<!'
    '-- SYS&#45;AGA&#45;&gt;CMP&#45;REPLAY&#45;BUFFER -->\n<g id="'
    'part_of:CMP&#45;REPLAY&#45;BUFFER:SYS&#45;AGA" class="edge">'
    "\n<title>SYS&#45;AGA&#45;&gt;CMP&#45;REPLAY&#45;BUFFER</title"
    '>\n<path fill="none" stroke="#526677" stroke-width="1.5" d="M'
    "2081.86,-360.25C2202,-344.15 2393.62,-313.51 2553.97,-265.36"
    ' 2563.94,-262.37 2574.2,-258.81 2584.32,-254.98"/>\n</g>\n<!--'
    ' SYS&#45;AGA&#45;&gt;CMP&#45;SAFETY&#45;FILTER -->\n<g id="pa'
    'rt_of:CMP&#45;SAFETY&#45;FILTER:SYS&#45;AGA" class="edge">\n<'
    "title>SYS&#45;AGA&#45;&gt;CMP&#45;SAFETY&#45;FILTER</title>\n"
    '<path fill="none" stroke="#526677" stroke-width="1.5" d="M20'
    "81.95,-369.44C2244.29,-360.45 2545.82,-335.12 2792.97,-265.3"
    '6 2803.08,-262.5 2813.46,-258.91 2823.63,-254.95"/>\n</g>\n<!-'
    '- SYS&#45;AGA&#45;&gt;CMP&#45;SCREEN&#45;CAPTURE -->\n<g id="'
    'part_of:CMP&#45;SCREEN&#45;CAPTURE:SYS&#45;AGA" class="edge"'
    ">\n<title>SYS&#45;AGA&#45;&gt;CMP&#45;SCREEN&#45;CAPTURE</tit"
    'le>\n<path fill="none" stroke="#526677" stroke-width="1.5" d='
    '"M2081.99,-372.59C2278.7,-367.59 2686.9,-347.25 3020.97,-265'
    '.36 3032.35,-262.57 3044.06,-258.99 3055.56,-255.01"/>\n</g>\n'
    "<!-- SYS&#45;AGA&#45;&gt;CMP&#45;SKILL&#45;TRAINER -->\n<g id"
    '="part_of:CMP&#45;SKILL&#45;TRAINER:SYS&#45;AGA" class="edge'
    '">\n<title>SYS&#45;AGA&#45;&gt;CMP&#45;SKILL&#45;TRAINER</tit'
    'le>\n<path fill="none" stroke="#526677" stroke-width="1.5" d='
    '"M2081.78,-369.63C2359.45,-357.96 3052.52,-323.73 3276.97,-2'
    '65.36 3287.41,-262.65 3298.08,-259.02 3308.5,-254.96"/>\n</g>'
    "\n<!-- SYS&#45;AGA&#45;&gt;CMP&#45;TEMPORAL&#45;STATE -->\n<g "
    'id="part_of:CMP&#45;TEMPORAL&#45;STATE:SYS&#45;AGA" class="e'
    'dge">\n<title>SYS&#45;AGA&#45;&gt;CMP&#45;TEMPORAL&#45;STATE<'
    '/title>\n<path fill="none" stroke="#526677" stroke-width="1.5'
    '" d="M2081.77,-370.64C2391.98,-360.43 3231.14,-327.72 3500.9'
    '7,-265.36 3512.58,-262.68 3524.51,-259.08 3536.18,-255.02"/>'
    "\n</g>\n<!-- SYS&#45;AGA&#45;&gt;CMP&#45;VISIBLE&#45;STATE&#45"
    ';BRIDGE -->\n<g id="part_of:CMP&#45;VISIBLE&#45;STATE&#45;BRI'
    'DGE:SYS&#45;AGA" class="edge">\n<title>SYS&#45;AGA&#45;&gt;CM'
    'P&#45;VISIBLE&#45;STATE&#45;BRIDGE</title>\n<path fill="none"'
    ' stroke="#526677" stroke-width="1.5" d="M2081.76,-371.17C242'
    "5.75,-361.61 3431.17,-328.85 3752.97,-265.36 3756.05,-264.75"
    ' 3759.16,-264.1 3762.28,-263.4"/>\n</g>\n</g>\n</svg>\n'
)
