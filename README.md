#Roi

A collection of tools for "data engineering" in the context of the Gnosis project.  


___

## profile


choco install graphviz
pip install snakeviz
pip install gprof2dot

gprof2dot -f pstats async.profile | dot -Tpng -o async.png
