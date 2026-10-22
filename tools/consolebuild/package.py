"""Package committed cel-shaded model previews; no Blender required."""
from tools.themebuild.consoles import build
from tools.themebuild.geometry import ROOT


def main():
    build(ROOT/'theme/art-book-slot/_slot')


if __name__=='__main__':main()
