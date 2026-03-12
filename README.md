# OpenDropTranslator

OpenDropTranslator is a microfluidic protocol compiler designed to translate operation graphs defined in DOT format into executable instruction sequences for OpenDrop digital microfluidic chips. This project implements a four-stage pipeline: graph parsing, scheduling, placement, and routing.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Core Pipeline](#core-pipeline)
- [Key Data Structures](#key-data-structures)
- [Common Developer Workflows](#common-developer-workflows)
- [Important Edge Cases](#important-edge-cases)
- [Contributing](#contributing)
- [License](#license)

## Installation

To install the necessary dependencies, run:

```bash
pip install -r requirements.txt
```

## Usage

To run the translation process, use the following command:

```bash
python translator.py <input.dot> <output.json> --module_topology <modules.json> --width 16 --height 8
```

## Core Pipeline

1. **Parse**: Load DOT graph and create `Op` objects with a dependency graph.
2. **Schedule**: Assign start and end times using list scheduling.
3. **Place**: Bind scheduled operations to physical `Module` instances.
4. **Route**: Find droplet paths between modules using Lee's algorithm.

## Key Data Structures

- **Op**: Represents an operation with properties like `start_time`, `end_time`, and dependency links.
- **Module**: Represents a physical chip location with position, type, and capacity.
- **Position**: Represents grid coordinates and includes interference region violation detection.
- **Route**: Stores source, destination, and path information.

## Common Developer Workflows

### Running Tests

To run the tests, execute:

```bash
python test.py
```

### Debugging Workflows

1. Check `scheduler` logic for scheduling issues.
2. Inspect `placer` for placement conflicts.
3. Debug routing failures using `router` output.
4. Validate output by checking your output json file.

## Important Edge Cases

- Handle scheduling deadlocks by adjusting `max_droplets`.
- Manage cases where no route is found by checking board size and interference zones.
- Ensure correct updates of `end_time` for module reuse.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for discussion.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
