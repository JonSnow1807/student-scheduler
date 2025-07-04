#!/bin/bash

# Variables
COMPARTMENT_ID="your-compartment-id"
CLUSTER_NAME="student-scheduler-cluster"
REGION="us-ashburn-1"

# Create OKE cluster
oci ce cluster create \
  --compartment-id $COMPARTMENT_ID \
  --name $CLUSTER_NAME \
  --kubernetes-version "v1.27.2" \
  --region $REGION

# Create node pool
oci ce node-pool create \
  --cluster-id $CLUSTER_ID \
  --compartment-id $COMPARTMENT_ID \
  --name "scheduler-nodes" \
  --node-shape "VM.Standard.E4.Flex" \
  --node-shape-config '{"memoryInGBs": 16, "ocpus": 2}' \
  --size 3

# Create container registry
oci artifacts container repository create \
  --compartment-id $COMPARTMENT_ID \
  --display-name "student-scheduler" \
  --is-public false
