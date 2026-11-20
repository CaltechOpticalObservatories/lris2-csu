# lris2csu
A demo package for the LRIS2 Configurable Slit Unit, showcasing remote client objects, hardware servers, 
zmq communication (with support for mKTL developments). 

## Installation
#Install miniconda


mkdir ~/src  #or wherever
cd ~/src  #or wherever

git clone https://github.com/CaltechOpticalObservatories/lris2-csu.git
git clone https://github.com/CaltechOpticalObservatories/coo-ethercat.git
git clone -b develop https://github.com/baileyji/mKTL.git mktl
cd lris2-csu
conda env create -f environment.yml
conda activate lris2csu
pip install pysoem
pip install -e ./coo-ethercat
pip install -e ./mktl
pip install -e ./lris2-csu


### Requirements

- Python 3.12 or higher
- `pip` (ensure it's the latest version)
- `setuptools` 42 or higher (for building the package)
- `cooethercat`


### Slit geometry

`lris2csu.geometry` holds the bar pair configuration and the conversions between
slits and bar positions, in mm or encoder counts, and imports nothing from
coo-ethercat. A pair may have only one bar placed; its slit then runs from that
bar's edge to the far end of the opening. A slit is validated before it is
converted: it must lie inside the opening and need only placed bars.

```python
from lris2csu.geometry import BarConfig, BarPairConfig, CSUHardwareConfig

csu = CSUHardwareConfig("eth0", [BarPairConfig(1, left=BarConfig(7))], None, None)
csu.compute_bar_mm_positions({1: (155.0, 210.0)})   # {7: 50.0}
```

Run the tests with `pytest`.


### Where to look, how to use (for now)

#### iPython play

Take a look at `lris2-csu/examples/demo.py` for local ipython commanding. 

`sudo /home/l2dev/miniconda3/bin/conda run -n lris2csu --no-capture-output ipython`


#### daemon/client ecosystem

Take a look at Take a look at lris2-csu/examples/mktl_play.py for remote control via "mktl" commanding. Note that this would need spinning up:
`sudo ip link set dev eno1  up`
- Three Terminals:
  - `conda run -n lris2csu python ~/src/mKTL/mktl/registry.py`
  - `sudo /home/l2dev/miniconda3/bin/conda run -n lris2csu --no-capture-output python ~/src/lris2-csu/lris2csu/manager.py --eth eno1 --cfg ~/src/lris2-csu/lris2csu/config/csu.yaml`
  - `conda run -n lris2csu python ~/src/mKTL/mktl/registry.py`
- Command Terminal
  - Start up ipython somewhere and instantiate `lris2-csu.remote.CSURemote()`


/Users/jibailey/src/lris2-csu/lris2csu/manager.py