"""
ml/training/train.py

Training pipeline for fine-tuning custom NLP urgency classification model.
Uses medical urgency corpus and implements LoRA for efficient training.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import torch
from datetime import datetime

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
    TextClassificationPipeline,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset, DatasetDict, load_metric
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
import mlflow
import mlflow.transformers

logger = logging.getLogger(__name__)


# ============================================================================
# TRAINING CONFIGURATION
# ============================================================================

class TrainingConfig:
    """Configuration for model training."""
    
    # Model
    BASE_MODEL = "facebook/bart-large-mnli"
    MAX_LENGTH = 512
    NUM_LABELS = 5  # ESI 1-5
    
    # Data
    TRAIN_TEST_SPLIT = 0.8
    VALIDATION_SPLIT = 0.1
    
    # Training
    BATCH_SIZE = 8
    LEARNING_RATE = 2e-4
    EPOCHS = 3
    WARMUP_STEPS = 500
    WEIGHT_DECAY = 0.01
    
    # LoRA (Parameter-Efficient Fine-Tuning)
    LORA_R = 8
    LORA_ALPHA = 16
    LORA_DROPOUT = 0.05
    
    # Callbacks
    EARLY_STOPPING_PATIENCE = 2
    SAVE_STRATEGY = "epoch"
    EVAL_STRATEGY = "epoch"
    
    # Paths
    OUTPUT_DIR = "models/checkpoints"
    DATA_DIR = "data/medical_urgency"
    METRICS_DIR = "metrics"


# ============================================================================
# TRAINING DATASET
# ============================================================================

class MedicalUrgencyDataset:
    """
    Load and prepare medical urgency classification dataset.
    
    Dataset structure:
    - Label 1: Life-threatening, immediate intervention needed
    - Label 2: Emergent, high acuity
    - Label 3: Urgent, moderate acuity
    - Label 4: Less urgent, low-moderate acuity
    - Label 5: Minor, minimal acuity
    """
    
    # Curated examples for medical urgency classification
    TRAINING_EXAMPLES = [
        # ESI 1: Life-threatening
        ("Unresponsive with no pulse, no respiration", 0),
        ("Severe difficulty breathing with cyanosis", 0),
        ("Severe trauma with massive bleeding", 0),
        ("Chest pain with hypotension and altered mental status", 0),
        ("Severe allergic reaction with airway compromise", 0),
        ("Acute stroke symptoms, slurred speech and weakness", 0),
        ("Severe sepsis with altered mental status", 0),
        ("Massive hemorrhage from any source", 0),
        
        # ESI 2: Emergent
        ("Chest pain with shortness of breath and diaphoresis", 1),
        ("Severe abdominal pain with rebound tenderness", 1),
        ("Head injury with loss of consciousness", 1),
        ("High fever with rash and neck stiffness", 1),
        ("Acute ST-elevation myocardial infarction", 1),
        ("Pulmonary embolism with hypoxia", 1),
        ("Acute coronary syndrome risk factors", 1),
        ("Altered mental status with fever", 1),
        ("Severe dyspnea, stridor, respiratory distress", 1),
        
        # ESI 3: Urgent
        ("Moderate chest pain, stable vitals", 2),
        ("Acute abdominal pain without severe symptoms", 2),
        ("Moderate head injury, alert", 2),
        ("Fever over 39C with mild symptoms", 2),
        ("Shortness of breath, moderate activity limitation", 2),
        ("Acute fracture with moderate pain", 2),
        ("Unilateral leg swelling and pain", 2),
        ("Moderate dehydration with tachycardia", 2),
        ("Acute asthma exacerbation, responsive to treatment", 2),
        
        # ESI 4: Less Urgent
        ("Mild headache, pressure sensation", 3),
        ("Mild abdominal cramping", 3),
        ("Minor cut with bleeding controlled", 3),
        ("Low-grade fever, feeling unwell", 3),
        ("Mild ankle sprain, able to bear weight", 3),
        ("Mild chest discomfort without cardiac risk", 3),
        ("Minor laceration, needs sutures", 3),
        ("Sore throat, no difficulty swallowing", 3),
        
        # ESI 5: Minor
        ("Twisted ankle playing football, swollen", 4),
        ("Minor abrasion, needs cleaning", 4),
        ("Insect bite with mild itching", 4),
        ("Small cut on finger", 4),
        ("Mild rash without systemic symptoms", 4),
        ("Minor muscle strain", 4),
        ("Blister on foot", 4),
        ("Mild allergic reaction to food", 4),
    ]
    
    @staticmethod
    def create_dataset(
        config: TrainingConfig,
        additional_data: Optional[List[Tuple[str, int]]] = None,
    ) -> DatasetDict:
        """
        Create training dataset.
        
        Args:
            config: Training configuration
            additional_data: Additional training examples (optional)
            
        Returns:
            HuggingFace DatasetDict with train/test/validation splits
        """
        # Combine base examples with additional data
        all_examples = MedicalUrgencyDataset.TRAINING_EXAMPLES.copy()
        if additional_data:
            all_examples.extend(additional_data)
        
        # Shuffle and split
        np.random.shuffle(all_examples)
        
        texts = [ex[0] for ex in all_examples]
        labels = [ex[1] for ex in all_examples]
        
        # Create dataset
        dataset = Dataset.from_dict({
            "text": texts,
            "label": labels,
        })
        
        # Split train/test
        split_dataset = dataset.train_test_split(
            test_size=1 - config.TRAIN_TEST_SPLIT,
            seed=42,
        )
        
        # Further split test into validation and test
        test_validation = split_dataset["test"].train_test_split(
            test_size=0.5,
            seed=42,
        )
        
        return DatasetDict({
            "train": split_dataset["train"],
            "validation": test_validation["train"],
            "test": test_validation["test"],
        })
    
    @staticmethod
    def preprocess_function(examples, tokenizer, max_length=512):
        """Tokenize and prepare examples for training."""
        return tokenizer(
            examples["text"],
            max_length=max_length,
            truncation=True,
            padding="max_length",
        )


# ============================================================================
# MODEL TRAINING
# ============================================================================

class MedicalTriageModelTrainer:
    """Train and evaluate medical triage NLP model."""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self.trainer = None
        
        logger.info(f"Trainer initialized. Device: {self.device}")
    
    def setup(self):
        """Initialize model and tokenizer."""
        logger.info(f"Loading tokenizer: {self.config.BASE_MODEL}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.BASE_MODEL)
        
        logger.info(f"Loading model: {self.config.BASE_MODEL}")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.config.BASE_MODEL,
            num_labels=self.config.NUM_LABELS,
            problem_type="single_label_classification",
        )
        
        # Apply LoRA
        logger.info("Applying LoRA (Parameter-Efficient Fine-Tuning)...")
        lora_config = LoraConfig(
            task_type=TaskType.SEQ_CLS,
            r=self.config.LORA_R,
            lora_alpha=self.config.LORA_ALPHA,
            lora_dropout=self.config.LORA_DROPOUT,
            bias="none",
        )
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
    
    def train(self, train_dataset: DatasetDict):
        """
        Train model on dataset.
        
        Args:
            train_dataset: HuggingFace DatasetDict
        """
        # Preprocess datasets
        logger.info("Preprocessing datasets...")
        processed_datasets = train_dataset.map(
            lambda x: MedicalUrgencyDataset.preprocess_function(
                x, self.tokenizer, self.config.MAX_LENGTH
            ),
            batched=True,
        )
        
        # Remove text column after tokenization
        processed_datasets = processed_datasets.remove_columns(["text"])
        processed_datasets = processed_datasets.rename_column("label", "labels")
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.config.OUTPUT_DIR,
            learning_rate=self.config.LEARNING_RATE,
            per_device_train_batch_size=self.config.BATCH_SIZE,
            per_device_eval_batch_size=self.config.BATCH_SIZE,
            num_train_epochs=self.config.EPOCHS,
            weight_decay=self.config.WEIGHT_DECAY,
            warmup_steps=self.config.WARMUP_STEPS,
            eval_strategy=self.config.EVAL_STRATEGY,
            save_strategy=self.config.SAVE_STRATEGY,
            logging_steps=10,
            load_best_model_at_end=True,
            metric_for_best_model="f1",
            greater_is_better=True,
            seed=42,
            report_to=["mlflow"],
            run_name=f"medical_triage_model_{datetime.now().isoformat()}",
        )
        
        # Initialize trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=processed_datasets["train"],
            eval_dataset=processed_datasets["validation"],
            compute_metrics=self._compute_metrics,
            callbacks=[
                EarlyStoppingCallback(
                    early_stopping_patience=self.config.EARLY_STOPPING_PATIENCE,
                    early_stopping_threshold=0.001,
                )
            ],
            tokenizer=self.tokenizer,
        )
        
        # Train
        logger.info("Starting training...")
        train_result = self.trainer.train()
        
        logger.info(f"✓ Training complete. Loss: {train_result.training_loss:.4f}")
        return train_result
    
    def evaluate(self, eval_dataset: DatasetDict) -> Dict:
        """
        Evaluate model on test set.
        
        Args:
            eval_dataset: DatasetDict with test split
            
        Returns:
            Dict with evaluation metrics
        """
        logger.info("Evaluating model on test set...")
        
        eval_results = self.trainer.evaluate(eval_dataset=eval_dataset["test"])
        
        # Compute additional metrics
        predictions, labels, _ = self.trainer.predict(eval_dataset["test"])
        pred_labels = np.argmax(predictions, axis=1)
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, pred_labels, average="weighted", zero_division=0
        )
        
        cm = confusion_matrix(labels, pred_labels)
        
        results = {
            **eval_results,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion_matrix": cm.tolist(),
        }
        
        logger.info(f"Evaluation results: F1={f1:.4f}, Precision={precision:.4f}, Recall={recall:.4f}")
        return results
    
    def save_model(self, output_path: str):
        """Save trained model."""
        logger.info(f"Saving model to {output_path}")
        os.makedirs(output_path, exist_ok=True)
        self.model.save_pretrained(output_path)
        self.tokenizer.save_pretrained(output_path)
        logger.info("✓ Model saved")
    
    def create_inference_pipeline(self, model_path: str) -> TextClassificationPipeline:
        """Create inference pipeline from saved model."""
        logger.info(f"Loading model for inference: {model_path}")
        
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        return TextClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else -1,
        )
    
    def _compute_metrics(self, eval_pred):
        """Compute metrics for evaluation."""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average="weighted", zero_division=0
        )
        
        accuracy = np.mean(predictions == labels)
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }


# ============================================================================
# MAIN TRAINING PIPELINE
# ============================================================================

def main():
    """Main training pipeline."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Configuration
    config = TrainingConfig()
    
    # Create output directories
    Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.METRICS_DIR).mkdir(parents=True, exist_ok=True)
    
    # Initialize MLflow
    mlflow.set_experiment("medical_triage_training")
    
    with mlflow.start_run():
        # Log hyperparameters
        mlflow.log_params({
            "base_model": config.BASE_MODEL,
            "learning_rate": config.LEARNING_RATE,
            "batch_size": config.BATCH_SIZE,
            "epochs": config.EPOCHS,
            "lora_r": config.LORA_R,
            "lora_alpha": config.LORA_ALPHA,
        })
        
        # 1. Create dataset
        logger.info("Creating dataset...")
        dataset = MedicalUrgencyDataset.create_dataset(config)
        logger.info(f"Dataset sizes: train={len(dataset['train'])}, val={len(dataset['validation'])}, test={len(dataset['test'])}")
        
        # 2. Setup trainer
        logger.info("Setting up trainer...")
        trainer = MedicalTriageModelTrainer(config)
        trainer.setup()
        
        # 3. Train
        logger.info("Training model...")
        train_result = trainer.train(dataset)
        mlflow.log_metric("training_loss", train_result.training_loss)
        
        # 4. Evaluate
        logger.info("Evaluating model...")
        eval_results = trainer.evaluate(dataset)
        
        for key, value in eval_results.items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(key, value)
        
        logger.info(f"\nFinal Results:")
        logger.info(f"  F1 Score: {eval_results.get('f1', 'N/A'):.4f}")
        logger.info(f"  Accuracy: {eval_results.get('accuracy', 'N/A'):.4f}")
        logger.info(f"  Precision: {eval_results.get('precision', 'N/A'):.4f}")
        logger.info(f"  Recall: {eval_results.get('recall', 'N/A'):.4f}")
        
        # 5. Save model
        model_path = f"{config.OUTPUT_DIR}/final_model"
        trainer.save_model(model_path)
        mlflow.log_artifact(model_path)
        
        logger.info("\n✓ Training pipeline complete!")


if __name__ == "__main__":
    main()
