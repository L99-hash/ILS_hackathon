"""
Robot Action Executor

Executes lerobot replay commands based on classified products
"""

import subprocess
import os
from typing import Optional, Tuple
from pathlib import Path


class RobotExecutor:
    """
    Executes robotic actions based on product classification

    Maps product classes to their corresponding lerobot replay commands
    """

    def __init__(self, robot_port: str = "/dev/ttyACM1", workspace_root: Optional[str] = None, calibration_dir: Optional[str] = None):
        """
        Initialize robot executor

        Args:
            robot_port: Serial port for robot communication (e.g., /dev/ttyACM1)
            workspace_root: Root directory of workspace (auto-detected if None)
            calibration_dir: Path to calibration directory (auto-detected if None)
        """
        self.robot_port = robot_port

        # Auto-detect workspace root if not provided
        if workspace_root is None:
            # Assume we're running from ILS_hackathon directory
            self.workspace_root = Path.cwd()
        else:
            self.workspace_root = Path(workspace_root)

        # Set calibration directory
        if calibration_dir is None:
            # Default to src/physical/calibration/robots/so_follower
            self.calibration_dir = self.workspace_root / "src" / "physical" / "calibration" / "robots" / "so_follower"
        else:
            self.calibration_dir = Path(calibration_dir)

        # Product to dataset mapping
        self.product_datasets = {
            "PCB-IND-100": "pick_PCB_IND_100",
            "MED-300": "pick_MED_300",
            "IOT-200": "pick_IOT_200",
            "AGR-400": "pick_AGR_400",
            "PCB-PWR-500": "pick_PCB_PWR_500",
            # Defect variants - use separate defect-specific datasets
            "PCB_IND_100_defect": "pick_PCB_IND_100_defect",
            "MED_300_defect": "pick_MED_300_defect",
        }

        print(f"🤖 Robot executor initialized")
        print(f"   Port: {self.robot_port}")
        print(f"   Workspace: {self.workspace_root}")
        print(f"   Calibration: {self.calibration_dir}")

    def get_replay_command(self, product_class: str, episode: int = 0) -> Optional[list]:
        """
        Get lerobot-replay command for a product class

        Args:
            product_class: Product class name (e.g., "PCB-IND-100")
            episode: Episode number to replay (default: 0)

        Returns:
            Command as list of arguments, or None if no action defined
        """
        dataset_name = self.product_datasets.get(product_class)

        if dataset_name is None:
            return None

        # Build dataset path relative to workspace root
        dataset_path = self.workspace_root / "src" / "physical" / "data" / dataset_name

        # Build command
        command = [
            "lerobot-replay",
            "--robot.type=so101_follower",
            f"--robot.port={self.robot_port}",
            "--robot.id=Follower",
            f"--robot.calibration_dir={self.calibration_dir}",
            f"--dataset.repo_id=local/{dataset_name}",
            f"--dataset.root={dataset_path}",
            f"--dataset.episode={episode}"
        ]

        return command

    def execute_action(self, product_class: str, episode: int = 0,
                       dry_run: bool = False) -> Tuple[bool, str]:
        """
        Execute robotic action for classified product

        Args:
            product_class: Classified product name
            episode: Episode number to replay
            dry_run: If True, only print command without executing

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Get command
        command = self.get_replay_command(product_class, episode)

        if command is None:
            message = f"⚠️  No robot action defined for: {product_class}"
            print(message)
            return False, message

        # Check if dataset exists
        # Extract dataset path from --dataset.root parameter (index 7 after adding calibration_dir)
        dataset_root_param = [param for param in command if param.startswith("--dataset.root=")][0]
        dataset_path = Path(dataset_root_param.split("=", 1)[1])

        if not dataset_path.exists():
            message = f"✗ Dataset not found: {dataset_path}"
            print(message)
            return False, message

        # Print command
        command_str = " \\\n    ".join(command)
        print(f"\n🤖 Executing robot action for: {product_class}")
        print(f"   Command: {command_str}")

        if dry_run:
            message = f"✓ [DRY RUN] Would execute action for {product_class}"
            print(message)
            return True, message

        # Execute command with real-time output
        print(f"⏳ Robot executing... (this may take 30-60 seconds)")

        try:
            # Use Popen for better control and output streaming
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=180)  # 3 minute timeout

                # Check if execution was successful
                if process.returncode == 0:
                    message = f"✓ Robot action completed for {product_class}"
                    print(message)
                    if stdout:
                        # Show last few lines of output
                        output_lines = stdout.strip().split('\n')
                        if len(output_lines) > 3:
                            print(f"   Output (last 3 lines):")
                            for line in output_lines[-3:]:
                                print(f"     {line[:100]}")
                        else:
                            print(f"   Output: {stdout[:300]}")
                    return True, message
                else:
                    # Failed but didn't crash - show error details
                    error_msg = stderr if stderr else stdout
                    message = f"✗ Robot action failed (exit code {process.returncode})"
                    print(message)
                    print(f"   Error details: {error_msg[:500]}")
                    return False, f"Robot execution failed: {error_msg[:200]}"

            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                message = f"✗ Robot action timed out after 180s for {product_class}"
                print(message)
                if stdout:
                    print(f"   Partial output: {stdout[:300]}")
                return False, message

        except FileNotFoundError:
            message = "✗ lerobot-replay command not found. Is lerobot installed?"
            print(message)
            print("   Install with: pip install lerobot")
            return False, message

        except Exception as e:
            message = f"✗ Unexpected error executing robot action: {str(e)[:200]}"
            print(message)
            return False, message

    def execute_for_classification(self, predicted_class: str, confidence: float,
                                   confidence_threshold: float = 0.7,
                                   dry_run: bool = False) -> Tuple[bool, str]:
        """
        Execute robot action based on classification result

        Only executes if confidence exceeds threshold

        Args:
            predicted_class: Classified product name
            confidence: Classification confidence (0-1)
            confidence_threshold: Minimum confidence to execute action
            dry_run: If True, only simulate execution

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check confidence threshold
        if confidence < confidence_threshold:
            message = (f"⚠️  Confidence too low ({confidence:.1%} < {confidence_threshold:.1%}), "
                      f"skipping robot action")
            print(message)
            return False, message

        # Execute action
        return self.execute_action(predicted_class, episode=0, dry_run=dry_run)

    def list_available_actions(self) -> dict:
        """
        List all available robot actions and their dataset paths

        Returns:
            Dictionary mapping product classes to dataset info
        """
        actions = {}

        for product, dataset_name in self.product_datasets.items():
            if dataset_name is None:
                actions[product] = {"available": False, "reason": "No action defined"}
                continue

            dataset_path = self.workspace_root / "src" / "physical" / "data" / dataset_name
            exists = dataset_path.exists()

            actions[product] = {
                "available": exists,
                "dataset": dataset_name,
                "path": str(dataset_path),
                "reason": "Ready" if exists else "Dataset not found"
            }

        return actions
