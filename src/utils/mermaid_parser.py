from typing import Dict, List, Optional, Tuple
import re

from pm4py import BPMN
from mermaid.graph import Graph

class MermaidToBPMNConverter:
    def __init__(self):
        self.bpmn = BPMN()
        self.node_map: Dict[str, BPMN.BPMNNode] = {}

    def parse_mermaid(self, mermaid_content: str) -> BPMN:
        """
        Parse Mermaid BPMN content and convert it to PM4PY BPMN object
        """
        # Reset state for new conversion
        self.bpmn = BPMN()
        self.node_map = {}

        # Clean and prepare the mermaid content
        lines = self._clean_mermaid_content(mermaid_content)

        # Process each line
        current_subprocess = None

        for line in lines:
            if line.strip().startswith('subgraph'):
                # Handle subprocess/pool
                subprocess_name = self._extract_subprocess_name(line)
                current_subprocess = self._create_subprocess(subprocess_name)
            elif line.strip() == 'end':
                current_subprocess = None
            elif '-->' in line or '-.->' in line:
                # Handle flows
                self._process_flow(line, current_subprocess)
            elif line.strip() and not line.strip().startswith('%'):
                # Handle nodes
                self._process_node(line, current_subprocess)

        return self.bpmn

    def _clean_mermaid_content(self, content: str) -> List[str]:
        """Clean and prepare mermaid content for parsing"""
        # Remove flowchart TB or other directives
        content = re.sub(r'flowchart\s+[A-Z]{2}', '', content)
        # Remove initialization configs
        content = re.sub(r'%%{.*?}%%', '', content, flags=re.DOTALL)
        # Split into lines and remove empty ones
        return [line.strip() for line in content.split('\n') if line.strip()]

    def _extract_subprocess_name(self, line: str) -> str:
        """Extract subprocess name from subgraph declaration"""
        match = re.search(r'subgraph\s+(\w+)\s*\[(.*?)\]', line)
        if match:
            return match.group(2)
        return "Default Pool"

    def _create_subprocess(self, name: str) -> BPMN.SubProcess:
        """Create a new subprocess/pool"""
        subprocess = BPMN.SubProcess(name=name)
        self.bpmn.add_node(subprocess)
        return subprocess

    def _process_node(self, line: str, subprocess: Optional[BPMN.SubProcess]) -> None:
        """Process a node declaration line"""
        # Extract node information
        match = re.search(r'(\w+)\[(.*?)\]', line)
        if not match:
            return

        node_id, node_name = match.groups()

        # Determine node type and create appropriate BPMN node
        node = self._create_node(node_id, node_name)

        if node:
            if subprocess:
                node.set_process(subprocess)
            self.bpmn.add_node(node)
            self.node_map[node_id] = node

    def _create_node(self, node_id: str, node_name: str) -> Optional[BPMN.BPMNNode]:
        """Create appropriate BPMN node based on context and naming"""
        if node_name.lower().startswith(('start', 'begin')):
            return BPMN.StartEvent(id=node_id, name=node_name)
        elif node_name.lower().startswith('end'):
            return BPMN.EndEvent(id=node_id, name=node_name)
        elif '?' in node_name:
            return BPMN.ExclusiveGateway(id=node_id, name=node_name)
        elif node_name.lower().startswith(('check', 'verify', 'validate')):
            return BPMN.Gateway(id=node_id, name=node_name)
        else:
            return BPMN.Task(id=node_id, name=node_name)

    def _process_flow(self, line: str, subprocess: Optional[BPMN.SubProcess]) -> None:
        """Process a flow declaration line"""
        # Handle both normal and dotted flows
        if '-->' in line:
            source, target = self._extract_flow_nodes(line, '-->')
            flow_type = BPMN.SequenceFlow
        elif '-.->' in line:
            source, target = self._extract_flow_nodes(line, '-.->')
            flow_type = BPMN.MessageFlow
        else:
            return

        if source in self.node_map and target in self.node_map:
            flow = flow_type(
                source=self.node_map[source],
                target=self.node_map[target]
            )
            if subprocess:
                flow.set_process(subprocess)
            self.bpmn.add_flow(flow)

    def _extract_flow_nodes(self, line: str, separator: str) -> Tuple[str, str]:
        """Extract source and target nodes from a flow declaration"""
        parts = line.split(separator)
        source = parts[0].strip()
        target = parts[1].strip()

        # Handle condition labels if present
        if '|' in target:
            target = target.split('|')[0].strip()

        return source, target

    def save_to_file(self, filename: str) -> None:
        """Save the BPMN object to a file (implementation depends on PM4PY's capabilities)"""
        # This would need to be implemented based on PM4PY's export capabilities
        pass