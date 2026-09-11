# Memory Diagnostics Report

This document details the system and process-level memory diagnostics performed to identify and resolve the Out-Of-Memory (OOM) blocker when loading `meta-llama/Llama-3.2-3B-Instruct` on a CPU-only Windows system.

## 1. System Memory Specifications

* **Total Physical RAM**: 15.40 GB
* **Initial Available RAM**: 6.23 GB (RAM Usage: 59.5%, Used: 9.17 GB)
* **Reclaimed Available RAM**: 8.38 GB (RAM Usage: 45.6%, after killing orphaned processes)
* **Swap/Page File Size**: 
  * **Initial Swap Size**: 2.93 GB (Used: 0.11 GB, Free: 2.82 GB)
  * **Maximum Virtual Memory (Page File)**: Up to 12.0 GB (configured as C:\pagefile.sys and D:\pagefile.sys with 3000MB initial / 6000MB maximum each)
* **System Commit Limit**: 
  * **Initial**: ~18.33 GB (15.40 GB RAM + 2.93 GB Swap)
  * **Maximum Expanded**: ~27.40 GB (15.40 GB RAM + 12.00 GB Swap)

## 2. Python Environment & Dependency Footprint

* **Python Version**: 3.11.9 (64-bit)
* **PyTorch Version**: 2.12.0+cpu (CPU-only build)
* **Transformers Version**: 4.57.6
* **Base Python Process Memory**: 
  * **Resident Set Size (RSS)**: ~394 MB
  * **Virtual Memory Size (VMS)**: ~1.03 GB

## 3. Memory Growth During Model Loading

### Step 1: Tokenizer Load
* **Process RSS**: Increased from ~394 MB to ~458 MB (+64 MB)
* **Process VMS**: Increased from ~1.03 GB to ~1.10 GB (+70 MB)
* **Status**: Highly stable; tokenizer cache footprint is optimized.

### Step 2: Naive Model Loading (4.96 GB Shard)
* **Attempted Configuration**: `torch_dtype=torch.float16`, `device_map="auto"`, low_cpu_mem_usage=True
* **Memory Allocation Behavior**: 
  * Hugging Face loaded shard 1 (`model-00001-of-00002.safetensors` - 4.96 GB).
  * SafeTensors attempted to memory-map (mmap) the 4.96 GB file.
  * Windows copy-on-write memory mapping allocated a commit charge matching the mapped size.
  * The process reached the system commit limit (~18.33 GB) due to concurrent allocations, resulting in a sudden silent crash (exit code 1) from a status in-page error (page fault failure) without Python traceback.

### Step 3: Local Sharded Model Loading (500 MB Shards)
* **Configured Layout**: Model weights split manually into 13 smaller shards of ~500 MB.
* **Loading with Runtime Offloading**:
  * **Constraints**: `max_memory={"cpu": "3.0GB"}`, `offload_folder="models/offload_runtime"`
  * **Process RSS**: ~0.729 GB
  * **Process VMS**: ~4.533 GB
  * **Status**: Successful loading and execution. Memory stayed strictly under the 3.0 GB RAM constraint. However, generation latency was high (~1.8s/token) due to sequential file swaps.
* **Loading Direct to CPU/RAM (Optimal)**:
  * **Constraints**: Loaded directly on CPU without explicit disk offloading (relying on Windows OS file paging).
  * **Process RSS**: ~0.730 GB (pages are loaded on-demand by OS)
  * **Process VMS**: ~7.443 GB
  * **Status**: Successful loading in **3.58 seconds** and generation in **4.77 seconds** (~0.3s/token). Swap space dynamically grew to **5.67 GB** to accommodate the virtual memory space.

## 4. CPU Memory Pressure & Bottlenecks

### Key Bottlenecks Identified:
1. **Large Shard Size**: Loading a single 4.96 GB file causes memory allocation spikes and forces Windows to map a large contiguous virtual memory block, triggering a status in-page error when memory is constrained.
2. **Commit Charge Limit**: The initial pagefile size (3 GB) limits the total commit charge. Windows crashes the process if it requests memory faster than the pagefile can expand.
3. **Orphaned Processes**: Orphaned Python processes from killed runs remained in memory, consuming **6.96 GB of RAM** and locking resources.

### Remediation Actions Applied:
1. **Resharding**: Split the model weights into 13 smaller chunks of ~500 MB each to reduce loading allocation spikes.
2. **Process Cleanup**: Terminated the orphaned Python process (PID 18236) to free up 6.96 GB of physical RAM.
3. **Paging Optimization**: Loaded the sharded model directly on CPU, allowing Windows to safely expand the swap file to 5.67 GB and manage tensor pages automatically.
