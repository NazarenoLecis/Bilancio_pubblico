from bilancio_pubblico.utils import BLACK, NAVY, ORANGE
from bilancio_pubblico.utils import create_post, format_percent, save_chart


def plot_peer_comparison(frame, title_lines, subtitle, filename, source, x_label="% del PIL"):
    sorted_frame = frame.sort_values("valore", ascending=True)
    colors = [ORANGE if row.codice == "IT" else NAVY for row in sorted_frame.itertuples(index=False)]
    fig, ax = create_post(title_lines, subtitle, axes_rect=[0.26, 0.315, 0.65, 0.42])
    ax.barh(sorted_frame["paese"], sorted_frame["valore"], color=colors)
    ax.set_xlabel(x_label, loc="left", labelpad=12)
    ax.grid(axis="x")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=14)
    ax.tick_params(axis="x", labelsize=13)
    max_value = float(sorted_frame["valore"].max())
    for index, row in enumerate(sorted_frame.itertuples(index=False)):
        ax.text(row.valore + max_value * 0.012, index, format_percent(row.valore), va="center", fontsize=13, fontweight="bold")
    ax.set_xlim(0, max_value * 1.18)
    save_chart(fig, filename, source)
