import java.awt.Color;
import java.awt.Font;
import java.io.File;
import java.io.IOException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.Set;

import org.gephi.graph.api.Edge;
import org.gephi.graph.api.Graph;
import org.gephi.graph.api.GraphController;
import org.gephi.graph.api.GraphModel;
import org.gephi.graph.api.GraphView;
import org.gephi.graph.api.Column;
import org.gephi.graph.api.Node;
import org.gephi.io.exporter.api.ExportController;
import org.gephi.io.exporter.preview.PNGExporter;
import org.gephi.io.importer.api.Container;
import org.gephi.io.importer.api.ImportController;
import org.gephi.layout.plugin.force.StepDisplacement;
import org.gephi.layout.plugin.force.yifanHu.YifanHuLayout;
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2;
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2Builder;
import org.gephi.preview.api.PreviewController;
import org.gephi.preview.api.PreviewModel;
import org.gephi.preview.api.PreviewProperty;
import org.gephi.preview.types.DependantColor;
import org.gephi.preview.types.DependantOriginalColor;
import org.gephi.preview.types.EdgeColor;
import org.gephi.project.api.ProjectController;
import org.gephi.project.api.Workspace;
import org.gephi.statistics.plugin.Modularity;
import org.openide.util.Lookup;

/**
 * Headless Gephi renderer for the two CSE 472 networks.
 *
 * Usage:
 *   java ... GephiRender information input.gexf output-directory
 *   java ... GephiRender users       input.gexf output-directory
 */
public final class GephiRender {
    private static final long RANDOM_SEED = 472L;
    private static final int IMAGE_WIDTH = 2400;
    private static final int IMAGE_HEIGHT = 1600;

    private static final Color[] COMMUNITY_COLORS = {
        new Color(0x2563EB), new Color(0xF97316), new Color(0x16A34A),
        new Color(0x9333EA), new Color(0xDC2626), new Color(0x0891B2),
        new Color(0xCA8A04), new Color(0xDB2777), new Color(0x4F46E5),
        new Color(0x059669), new Color(0xEA580C), new Color(0x7C3AED)
    };

    private GephiRender() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            System.err.println("Usage: GephiRender <information|users> <input.gexf> <output-dir>");
            System.exit(2);
        }

        String mode = args[0].toLowerCase(Locale.ROOT);
        if (!mode.equals("information") && !mode.equals("users")) {
            throw new IllegalArgumentException("Mode must be 'information' or 'users'.");
        }

        File input = new File(args[1]).getCanonicalFile();
        File outputDirectory = new File(args[2]).getCanonicalFile();
        if (!input.isFile()) {
            throw new IOException("Input GEXF does not exist: " + input);
        }
        if (!outputDirectory.isDirectory() && !outputDirectory.mkdirs()) {
            throw new IOException("Could not create output directory: " + outputDirectory);
        }

        render(mode, input, outputDirectory);
    }

    private static void render(String mode, File input, File outputDirectory) throws Exception {
        ImportController importController = Lookup.getDefault().lookup(ImportController.class);
        Container container = importController.importFile(input);
        if (!container.verify()) {
            throw new IOException("Gephi rejected the imported graph: " + input);
        }

        Workspace workspace = importController.process(container);
        GraphModel graphModel = Lookup.getDefault()
            .lookup(GraphController.class)
            .getGraphModel(workspace);
        Graph graph = graphModel.getGraph();

        initialisePositions(graph);
        if (mode.equals("information")) {
            runForceAtlas2(graphModel, 550);
            styleInformationGraph(graphModel, graph);
        } else {
            runYifanHu(graphModel, 350);
            styleUserGraph(graphModel, graph);
        }
        packComponents(graph);
        configurePreview(workspace, mode.equals("information"));

        String stem = mode.equals("information")
            ? "information_diffusion_gephi"
            : "user_network_gephi";

        File pngFile = new File(outputDirectory, stem + ".png");
        File gexfFile = new File(outputDirectory, stem + ".gexf");
        File projectFile = new File(outputDirectory, stem + ".gephi");

        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);
        exportController.exportFile(gexfFile, workspace);
        Lookup.getDefault().lookup(ProjectController.class)
            .saveProject(workspace.getProject(), projectFile);
        exportConnectedPng(graphModel, graph, workspace, pngFile);

        System.out.printf(
            Locale.ROOT,
            "%s: nodes=%d edges=%d png=%s gexf=%s project=%s%n",
            mode,
            graph.getNodeCount(),
            graph.getEdgeCount(),
            pngFile,
            gexfFile,
            projectFile
        );
    }

    private static void initialisePositions(Graph graph) {
        Random random = new Random(RANDOM_SEED);
        for (Node node : graph.getNodes()) {
            double angle = random.nextDouble() * Math.PI * 2.0;
            double radius = 50.0 + random.nextDouble() * 950.0;
            node.setPosition(
                (float) (Math.cos(angle) * radius),
                (float) (Math.sin(angle) * radius)
            );
        }
    }

    private static void runForceAtlas2(GraphModel graphModel, int iterations) {
        ForceAtlas2 layout = new ForceAtlas2Builder().buildLayout();
        layout.setGraphModel(graphModel);
        layout.resetPropertiesValues();
        layout.setInitialisationSeed(RANDOM_SEED);
        layout.setBarnesHutOptimize(Boolean.FALSE);
        layout.setScalingRatio(14.0);
        layout.setGravity(1.6);
        layout.setJitterTolerance(0.8);
        layout.setLinLogMode(Boolean.TRUE);
        layout.setOutboundAttractionDistribution(Boolean.TRUE);
        layout.setAdjustSizes(Boolean.FALSE);
        layout.initAlgo();
        for (int i = 0; i < iterations && layout.canAlgo(); i++) {
            layout.goAlgo();
        }
        layout.endAlgo();
    }

    private static void runYifanHu(GraphModel graphModel, int iterations) {
        YifanHuLayout layout = new YifanHuLayout(null, new StepDisplacement(1f));
        layout.setGraphModel(graphModel);
        layout.resetPropertiesValues();
        layout.setOptimalDistance(180f);
        layout.setRelativeStrength(0.25f);
        layout.setAdaptiveCooling(Boolean.TRUE);
        layout.initAlgo();
        for (int i = 0; i < iterations && layout.canAlgo(); i++) {
            layout.goAlgo();
        }
        layout.endAlgo();
    }

    private static void styleInformationGraph(GraphModel graphModel, Graph graph) {
        Set<Node> labelled = highestDegreeNodes(graph, 5);
        int maxDegree = maxDegree(graph);
        Column isReplyColumn = findColumnByTitle(graphModel, "is_reply");
        Column isReblogColumn = findColumnByTitle(graphModel, "is_reblog");
        Color rootColor = new Color(0xF97316);
        Color replyColor = new Color(0x2563EB);
        Color reblogColor = new Color(0x7C3AED);

        for (Node node : graph.getNodes()) {
            int degree = graph.getDegree(node);
            node.setSize(sizeForDegree(degree, maxDegree, 5.0f, 32.0f));
            if (booleanAttribute(node, isReblogColumn)) {
                node.setColor(reblogColor);
            } else if (booleanAttribute(node, isReplyColumn)) {
                node.setColor(replyColor);
            } else {
                node.setColor(rootColor);
            }
            configureLabel(node, labelled.contains(node), 9f, 42);
        }
        styleEdges(graph, new Color(0x94A3B8), 0.36f);
    }

    private static void styleUserGraph(GraphModel graphModel, Graph graph) {
        Modularity modularity = new Modularity();
        modularity.setRandom(false);
        modularity.setResolution(1.0);
        modularity.setUseWeight(true);
        modularity.execute(graphModel);

        Column modularityColumn = findColumnByTitle(graphModel, Modularity.MODULARITY_CLASS);
        Set<Node> labelled = highestDegreeNodes(graph, 1);
        int maxDegree = maxDegree(graph);
        for (Node node : graph.getNodes()) {
            int degree = graph.getDegree(node);
            node.setSize(sizeForDegree(degree, maxDegree, 6.0f, 38.0f));
            if (degree == 0) {
                node.setColor(new Color(0xCBD5E1));
            } else {
                Object community = modularityColumn == null ? null : node.getAttribute(modularityColumn);
                int index = community instanceof Number ? ((Number) community).intValue() : 0;
                node.setColor(COMMUNITY_COLORS[Math.floorMod(index, COMMUNITY_COLORS.length)]);
            }
            configureLabel(node, labelled.contains(node), 9f, 24);
        }
        styleEdges(graph, new Color(0x64748B), 0.42f);
    }

    private static void styleEdges(Graph graph, Color color, float alpha) {
        for (Edge edge : graph.getEdges()) {
            edge.setColor(color);
            edge.setAlpha(alpha);
        }
    }

    private static void configureLabel(Node node, boolean visible, float size, int maxCharacters) {
        String label = node.getLabel() == null ? String.valueOf(node.getId()) : node.getLabel();
        if (label.length() > maxCharacters) {
            label = label.substring(0, maxCharacters - 1) + "…";
        }
        node.getTextProperties().setText(label);
        node.getTextProperties().setVisible(visible);
        node.getTextProperties().setSize(size);
        node.getTextProperties().setColor(new Color(0x0F172A));
    }

    private static void configurePreview(Workspace workspace, boolean directed) {
        PreviewController previewController = Lookup.getDefault().lookup(PreviewController.class);
        PreviewModel model = previewController.getModel(workspace);
        model.getProperties().putValue(PreviewProperty.BACKGROUND_COLOR, Color.WHITE);
        model.getProperties().putValue(PreviewProperty.SHOW_EDGES, Boolean.TRUE);
        model.getProperties().putValue(PreviewProperty.DIRECTED, directed);
        model.getProperties().putValue(PreviewProperty.EDGE_COLOR, new EdgeColor(new Color(0x94A3B8)));
        model.getProperties().putValue(PreviewProperty.EDGE_OPACITY, 58);
        model.getProperties().putValue(PreviewProperty.EDGE_THICKNESS, directed ? 1.0f : 1.2f);
        model.getProperties().putValue(PreviewProperty.ARROW_SIZE, directed ? 7f : 0f);
        model.getProperties().putValue(PreviewProperty.NODE_SCALE_FACTOR, 1.15f);
        model.getProperties().putValue(PreviewProperty.NODE_OPACITY, 96);
        model.getProperties().putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.7f);
        model.getProperties().putValue(
            PreviewProperty.NODE_BORDER_COLOR,
            new DependantColor(new Color(0x334155))
        );
        model.getProperties().putValue(PreviewProperty.SHOW_NODE_LABELS, Boolean.TRUE);
        model.getProperties().putValue(PreviewProperty.NODE_LABEL_PROPORTIONAL_SIZE, Boolean.FALSE);
        model.getProperties().putValue(PreviewProperty.NODE_LABEL_AVOID_OVERLAP, Boolean.TRUE);
        model.getProperties().putValue(
            PreviewProperty.NODE_LABEL_COLOR,
            new DependantOriginalColor(new Color(0x0F172A))
        );
        model.getProperties().putValue(
            PreviewProperty.NODE_LABEL_FONT,
            new Font("SansSerif", Font.PLAIN, directed ? 8 : 9)
        );
        model.getProperties().putValue(PreviewProperty.NODE_LABEL_OUTLINE_SIZE, 3f);
        model.getProperties().putValue(PreviewProperty.NODE_LABEL_OUTLINE_OPACITY, 85);
        model.getProperties().putValue(
            PreviewProperty.NODE_LABEL_OUTLINE_COLOR,
            new DependantColor(Color.WHITE)
        );
        previewController.refreshPreview(workspace);
    }

    private static void exportPng(Workspace workspace, File output) throws IOException {
        ExportController exportController = Lookup.getDefault().lookup(ExportController.class);
        PNGExporter exporter = (PNGExporter) exportController.getExporter("png");
        exporter.setWorkspace(workspace);
        exporter.setWidth(IMAGE_WIDTH);
        exporter.setHeight(IMAGE_HEIGHT);
        exporter.setMargin(70);
        exporter.setTransparentBackground(false);
        exportController.exportFile(output, exporter);
    }

    private static void exportConnectedPng(
        GraphModel graphModel,
        Graph graph,
        Workspace workspace,
        File output
    ) throws IOException {
        GraphView originalView = graphModel.getVisibleView();
        GraphView connectedView = graphModel.createView(
            node -> graph.getDegree(node) > 0,
            edge -> true
        );
        graphModel.setVisibleView(connectedView);
        try {
            Lookup.getDefault().lookup(PreviewController.class).refreshPreview(workspace);
            exportPng(workspace, output);
        } finally {
            graphModel.setVisibleView(originalView);
            graphModel.destroyView(connectedView);
            Lookup.getDefault().lookup(PreviewController.class).refreshPreview(workspace);
        }
    }

    private static int maxDegree(Graph graph) {
        int max = 1;
        for (Node node : graph.getNodes()) {
            max = Math.max(max, graph.getDegree(node));
        }
        return max;
    }

    private static float sizeForDegree(int degree, int maxDegree, float minimum, float maximum) {
        double scaled = Math.sqrt((double) degree / (double) Math.max(1, maxDegree));
        return (float) (minimum + (maximum - minimum) * scaled);
    }

    private static Set<Node> highestDegreeNodes(Graph graph, int count) {
        List<Node> nodes = new ArrayList<>();
        for (Node node : graph.getNodes()) {
            nodes.add(node);
        }
        nodes.sort(
            Comparator.comparingInt((Node node) -> graph.getDegree(node))
                .reversed()
                .thenComparing(node -> String.valueOf(node.getId()))
        );
        Set<Node> result = new HashSet<>();
        for (int i = 0; i < Math.min(count, nodes.size()); i++) {
            if (graph.getDegree(nodes.get(i)) > 0) {
                result.add(nodes.get(i));
            }
        }
        return result;
    }

    private static boolean booleanAttribute(Node node, Column column) {
        if (column == null) {
            return false;
        }
        Object value = node.getAttribute(column);
        if (value instanceof Boolean) {
            return (Boolean) value;
        }
        if (value instanceof Number) {
            return ((Number) value).intValue() != 0;
        }
        return value != null && Boolean.parseBoolean(value.toString());
    }

    private static Column findColumnByTitle(GraphModel graphModel, String title) {
        Column byId = graphModel.getNodeTable().getColumn(title);
        if (byId != null) {
            return byId;
        }
        for (Column column : graphModel.getNodeTable()) {
            if (title.equals(column.getTitle())) {
                return column;
            }
        }
        return null;
    }

    private static void packComponents(Graph graph) {
        Set<Node> unseen = new HashSet<>();
        for (Node node : graph.getNodes()) {
            unseen.add(node);
        }

        List<List<Node>> components = new ArrayList<>();
        while (!unseen.isEmpty()) {
            Node start = unseen.iterator().next();
            unseen.remove(start);
            List<Node> component = new ArrayList<>();
            Deque<Node> queue = new ArrayDeque<>();
            queue.add(start);
            while (!queue.isEmpty()) {
                Node current = queue.removeFirst();
                component.add(current);
                for (Edge edge : graph.getEdges(current)) {
                    Node neighbor = graph.getOpposite(current, edge);
                    if (unseen.remove(neighbor)) {
                        queue.addLast(neighbor);
                    }
                }
            }
            components.add(component);
        }

        components.sort(
            Comparator.comparingInt((List<Node> component) -> component.size())
                .reversed()
                .thenComparing(component -> String.valueOf(component.get(0).getId()))
        );

        List<Node> isolates = new ArrayList<>();
        int packedIndex = 0;
        double furthestCenter = 0.0;
        final double goldenAngle = Math.PI * (3.0 - Math.sqrt(5.0));
        for (List<Node> component : components) {
            if (component.size() == 1) {
                isolates.add(component.get(0));
                continue;
            }

            double centerX;
            double centerY;
            if (packedIndex == 0) {
                centerX = 0.0;
                centerY = 0.0;
            } else {
                double angle = packedIndex * goldenAngle;
                double radius = 200.0 + 70.0 * Math.sqrt(packedIndex);
                centerX = Math.cos(angle) * radius;
                centerY = Math.sin(angle) * radius;
                furthestCenter = Math.max(furthestCenter, radius);
            }

            double sourceCenterX = 0.0;
            double sourceCenterY = 0.0;
            for (Node node : component) {
                sourceCenterX += node.x();
                sourceCenterY += node.y();
            }
            sourceCenterX /= component.size();
            sourceCenterY /= component.size();

            double sourceRadius = 1.0;
            for (Node node : component) {
                sourceRadius = Math.max(
                    sourceRadius,
                    Math.hypot(node.x() - sourceCenterX, node.y() - sourceCenterY)
                );
            }
            double targetRadius = 38.0 + 18.0 * Math.sqrt(component.size());
            double scale = targetRadius / sourceRadius;
            for (Node node : component) {
                node.setPosition(
                    (float) (centerX + (node.x() - sourceCenterX) * scale),
                    (float) (centerY + (node.y() - sourceCenterY) * scale)
                );
            }
            packedIndex++;
        }

        isolates.sort(Comparator.comparing(node -> String.valueOf(node.getId())));
        if (isolates.isEmpty()) {
            return;
        }
        double firstRadius = Math.max(650.0, furthestCenter + 200.0);
        int perRing = Math.max(32, (int) Math.ceil(Math.sqrt(isolates.size()) * 6.0));
        for (int index = 0; index < isolates.size(); index++) {
            int ring = index / perRing;
            int offset = index % perRing;
            int itemsOnRing = Math.min(perRing, isolates.size() - ring * perRing);
            double angle = (Math.PI * 2.0 * offset / itemsOnRing) + ring * 0.13;
            double radius = firstRadius + ring * 105.0;
            isolates.get(index).setPosition(
                (float) (Math.cos(angle) * radius),
                (float) (Math.sin(angle) * radius)
            );
        }
    }
}
