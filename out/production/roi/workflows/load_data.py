import matplotlib.pyplot as plt
import networkx
from networkx import draw
from networkx import isolates

from roi_web.processing import load_processed


def main():
    g = networkx.Graph()
    for el in load_processed():
        if el.neighbors:
            for n in el.neighbors:
                if el.url != n:
                    g.add_edge( el.url, n )

    h = networkx.Graph()
    for (left, right) in g.edges():
        if g.degree( left ) >= 10 and g.degree( right ) >= 10:
            h.add_edge(left, right)


    draw( h )
    plt.show()
    print()


if __name__ == "__main__":
    main()
