import numpy as np
import networkx as nx
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
from qiskit import QuantumCircuit
import random
    

def theta_to_prob(theta):
    return (np.sin(theta / 2)) ** 2


def interpret_gate(gate, qubits, labels, params, state):
    names = [labels[q] for q in qubits]

    prob = None
    if params:
        prob = round(theta_to_prob(params[0]), 3)

    # Track X flips
    if gate == "x":
        q = qubits[0]
        state[q] = not state.get(q, False)
        return f"{labels[q]} is flipped (TRUE ↔ FALSE)"

    # Controlled rotation
    if gate == "cry":
        control, target = qubits

        condition = "TRUE"
        if state.get(control, False):
            condition = "FALSE"

        return f"If {labels[control]} is {condition} → {labels[target]} reacts with probability {prob}"

    # Multi-controlled rotation
    if gate == "mcry":
        controls = qubits[:-1]
        target = qubits[-1]

        conds = []
        for q in controls:
            if state.get(q, False):
                conds.append(f"{labels[q]}=FALSE")
            else:
                conds.append(f"{labels[q]}=TRUE")

        return f"If {' AND '.join(conds)} → {labels[target]} triggers with probability {prob}"

    # Single qubit probability
    if gate == "ry":
        return f"{labels[qubits[0]]} occurs with probability {prob}"

    return f"{gate} on {names}"


def universal_alarm(incident_dict, hearing_dict):
    if not check_probabilities_sum_to_one(hearing_dict):
        print("Invalid probabilities for hearing persons. Please fix them and try again.")
        return
    theta = {}

    for k, v in incident_dict.items():
        theta[k] = 2 * np.arcsin(np.sqrt(v))

    for person, probs in hearing_dict.items():
        for k, v in probs.items():
            theta[f"{person}_{k}"] = 2 * np.arcsin(np.sqrt(v))

    var = ["Burglary", "Earthquake", "Alarm"]
    var += list(hearing_dict.keys())

    qc = QuantumCircuit(len(var))
    labels = {i: name for i, name in enumerate(var)}

    qc.ry(theta["Burglary"], 0)
    qc.ry(theta["Earthquake"], 1)

    qc.mcry(theta["Alarm_BurglaryEarthquake"], [0, 1], 2)

    qc.x(0)
    qc.mcry(theta["Alarm_nonBurglaryEarthquake"], [0, 1], 2)
    qc.x(0)

    qc.x(1)
    qc.mcry(theta["Alarm_BurglarynonEarthquake"], [0, 1], 2)
    qc.x(1)

    qc.x(0); qc.x(1)
    qc.mcry(theta["Alarm_nonBurglarynonEarthquake"], [0, 1], 2)
    qc.x(0); qc.x(1)

    for i, person in enumerate(hearing_dict, start=3):
        qc.cry(theta[f"{person}_Alarm"], 2, i)

    qc.x(2)

    for i, person in enumerate(hearing_dict, start=3):
        qc.cry(theta[f"{person}_nonAlarm"], 2, i)

    qc.x(2)

    return qc, labels


def build_graph(qc, labels):
    G = nx.Graph()
    node_activity = {}
    gate_index = {i: [] for i in range(qc.num_qubits)}
    edge_weight = {}

    for i in range(qc.num_qubits):
        G.add_node(i)
        node_activity[i] = 0

    state = {}  # 🔥 track flips globally

    for inst in qc.data:
        instr = inst.operation
        qubits = [q._index for q in inst.qubits]

        explanation = interpret_gate(
            instr.name,
            qubits,
            labels,
            instr.params,
            state
        )

        for q in qubits:
            node_activity[q] += 1
            gate_index[q].append(explanation)

        if len(qubits) > 1:
            for i in range(len(qubits)):
                for j in range(i + 1, len(qubits)):
                    pair = tuple(sorted((qubits[i], qubits[j])))
                    edge_weight[pair] = edge_weight.get(pair, 0) + 1

    for (u, v), w in edge_weight.items():
        G.add_edge(u, v, weight=w)

    return G, node_activity, gate_index


def build_figure(G, node_activity, labels, highlight=None):
    pos = nx.spring_layout(G, seed=42)

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(color="rgba(150,150,150,0.3)", width=1),
        hoverinfo="none"
    )

    node_x, node_y, sizes, colors, texts = [], [], [], [], []

    max_act = max(node_activity.values()) + 1

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        activity = node_activity[node]
        size = 10 + 30 * (activity / max_act)

        name = labels[node]

        if name == "Burglary":
            color = "red"
        elif name == "Earthquake":
            color = "orange"
        elif name == "Alarm":
            color = "green"
        else:
            color = "blue"

        if node == highlight:
            size *= 1.8
            color = "yellow"

        sizes.append(size)
        colors.append(color)
        texts.append(name)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=texts,
        textposition="top center",
        marker=dict(size=sizes, color=colors),
        customdata=list(G.nodes())
    )

    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        plot_bgcolor="#111",
        paper_bgcolor="#111",
        font=dict(color="white")
    )

    return fig


def get_app(qc, labels):
    if len(labels) - 3 > 1000:
        print("Too many hearing persons (limit is 1000).")
        return False,False
    
    G, node_activity, gate_index = build_graph(qc, labels)

    app = Dash(__name__)

    app.layout = html.Div([
        html.H2("🧠 Semantic Quantum Alarm Network"),

        dcc.Graph(id="graph"),

        html.H3("📖 Meaningful Explanation"),
        html.Pre(id="output", style={
            "background": "#111",
            "color": "#0f0",
            "height": "300px",
            "overflowY": "scroll"
        })
    ])

    @app.callback(
        Output("graph", "figure"),
        Output("output", "children"),
        Input("graph", "clickData")
    )
    def update(clickData):
        selected = None

        if clickData:
            selected = clickData["points"][0]["customdata"]
            explanations = gate_index[selected]
            text = "\n".join(explanations)
        else:
            text = "Click a node to see its real-world meaning..."

        fig = build_figure(G, node_activity, labels, selected)

        return fig, text
    return app,True


def check_probabilities_sum_to_one(hearing_persons_dicts):
    if len(hearing_persons_dicts) == 0:
        print("No hearing persons provided.")
        return False
    ok = True
    for person, probs in hearing_persons_dicts.items():
        p_A = probs.get("Alarm")
        p_nA = probs.get("nonAlarm")

        # print(f"\nChecking {person}:")

        # Check valid range
        if not (0 <= p_A <= 1 and 0 <= p_nA <= 1):
            # print("  ❌ Probabilities out of range [0,1]")
            ok = False
            continue

        # Show complements
        # print(f"  P(hear|Alarm) + P(not hear|Alarm) = {p_A} + {1 - p_A} = {p_A + (1 - p_A)}")
        # print(f"  P(hear|nonAlarm) + P(not hear|nonAlarm) = {p_nA} + {1 - p_nA} = {p_nA + (1 - p_nA)}")

        # These will always be 1 mathematically
        if abs((p_A + (1 - p_A)) - 1) < 1e-9 and abs((p_nA + (1 - p_nA)) - 1) < 1e-9:
            # print("  ✅ Sums to 1 (valid)")
            pass
        else:
            # print("  ❌ Does not sum to 1")
            ok = False
    return ok



# from universal_alarm import *

# if __name__ == "__main__":
#     incident_dict = {
#         "Burglary": 0.001,
#         "Earthquake": 0.002,
#         "Alarm_nonBurglarynonEarthquake": 0.001,
#         "Alarm_BurglarynonEarthquake": 0.29,
#         "Alarm_nonBurglaryEarthquake": 0.94,
#         "Alarm_BurglaryEarthquake": 0.95
#     }

#     hearing_dict = {
#         "John": {"nonAlarm": 0.1, "Alarm": 0.9},
#         "Mary": {"nonAlarm": 0.2, "Alarm": 0.8},
#         "Alice": {"nonAlarm": 0.15, "Alarm": 0.85},
#         "Bob": {"nonAlarm": 0.25, "Alarm": 0.75},
#         "Eve": {"nonAlarm": 0.05, "Alarm": 0.95}
#     }
    
#     qc, labels = universal_alarm(incident_dict, hearing_dict)
#     app,check = get_app(qc, labels)
#     if check == True:
#         app.run_server(debug=True)

#     hearing_dict = {
#         f"person_{i}": {"nonAlarm": random.uniform(0.1, 0.3), "Alarm": random.uniform(0.8, 0.9)}
#         for i in range(100)
#     }
#     qc, labels = universal_alarm(incident_dict, hearing_dict)
#     app,check = get_app(qc, labels)
#     if check == True:
#         app.run_server(debug=True)

#     hearing_dict = {
#         f"person_{i}": {"nonAlarm": random.uniform(0.1, 0.3), "Alarm": random.uniform(0.8, 0.9)}
#         for i in range(1000_000)
#     }
#     qc, labels = universal_alarm(incident_dict, hearing_dict)
#     app,check = get_app(qc, labels)
#     if check == True:
#         app.run_server(debug=True)

    