use anyhow::{Context, Result};
use chrono::Utc;
use governor::{Quota, RateLimiter};
use serde::Serialize;
use std::env;
use std::fs;
use std::process::Command;
use std::sync::Arc;
use std::time::Duration;
use tokio::time::Instant;
use uuid::Uuid;

#[derive(Debug, Serialize)]
struct RequestRecord {
    request_id: String,
    timestamp: String,
    endpoint: String,
    duration_ms: u64,
    status: String,
    response_size: usize,
}

#[derive(Debug, Serialize)]
struct ExecutionSummary {
    run_id: String,
    start_time: String,
    end_time: String,
    total_requests: usize,
    successful_requests: usize,
    failed_requests: usize,
    total_duration_secs: f64,
    rate_limit_config: RateLimitConfig,
    requests: Vec<RequestRecord>,
}

#[derive(Debug, Serialize, Clone, Copy)]
struct RateLimitConfig {
    requests_per_second: u32,
    burst_size: u32,
}

#[tokio::main]
async fn main() -> Result<()> {
    println!("{}", "=".repeat(80));
    println!("Snowflake Container Services - Enhanced API Demo");
    println!("Features: Secrets, Rate Limiting, File Persistence to Stage");
    println!("{}", "=".repeat(80));
    println!();

    // Read configuration from environment variables
    let api_key = env::var("API_KEY")
        .context("API_KEY environment variable not found")?;
    
    let api_endpoint = env::var("API_ENDPOINT")
        .unwrap_or_else(|_| "https://api.publicapis.org/entries".to_string());

    let num_requests = env::var("NUM_REQUESTS")
        .ok()
        .and_then(|v| v.parse::<usize>().ok())
        .unwrap_or(10);

    let rate_limit = env::var("RATE_LIMIT")
        .ok()
        .and_then(|v| v.parse::<u32>().ok())
        .unwrap_or(2);

    let stage_path = env::var("STAGE_PATH")
        .unwrap_or_else(|_| "@api_results_stage".to_string());

    println!("📋 Configuration:");
    println!("  API Endpoint: {}", api_endpoint);
    println!("  API Key (first 4 chars): {}...", &api_key.chars().take(4).collect::<String>());
    println!("  Number of Requests: {}", num_requests);
    println!("  Rate Limit: {} requests/second", rate_limit);
    println!("  Stage Path: {}", stage_path);
    println!();

    // Create rate limiter using token bucket algorithm
    // The governor crate implements a GCRA (Generic Cell Rate Algorithm) which is
    // equivalent to a token bucket with zero initial burst
    let rate_limit_config = RateLimitConfig {
        requests_per_second: rate_limit,
        burst_size: rate_limit.max(1),
    };
    
    let rate_nz = std::num::NonZeroU32::new(rate_limit)
        .context("Rate limit must be greater than 0")?;
    let burst_nz = std::num::NonZeroU32::new(rate_limit_config.burst_size)
        .context("Burst size must be greater than 0")?;
    
    let quota = Quota::per_second(rate_nz).allow_burst(burst_nz);
    let limiter = Arc::new(RateLimiter::direct(quota));

    println!("🚦 Rate Limiter Configured:");
    println!("  Quota: {} requests per second", rate_limit_config.requests_per_second);
    println!("  Burst Size: {}", rate_limit_config.burst_size);
    println!();

    // Execute rate-limited API requests
    println!("🚀 Starting {} rate-limited API requests...", num_requests);
    println!("{}", "-".repeat(80));

    let run_id = Uuid::new_v4().to_string();
    let start_time = Utc::now();
    let overall_start = Instant::now();
    
    let mut records = Vec::new();
    let mut successful = 0;
    let mut failed = 0;

    for i in 1..=num_requests {
        // Rate limiting: Block until we're allowed to make the next request
        // This demonstrates throttling by spacing requests according to our quota
        limiter.until_ready().await;
        
        let request_start = Instant::now();
        let request_id = Uuid::new_v4();
        
        print!("Request {}/{}: ", i, num_requests);
        
        let (status_str, response_size) = match make_api_request(&api_endpoint, &api_key).await {
            Ok(response) => {
                let duration = request_start.elapsed();
                let response_str = serde_json::to_string(&response)
                    .unwrap_or_else(|_| String::from("{}"));
                let size = response_str.len();
                
                println!("✅ SUCCESS ({}ms, {} bytes)", duration.as_millis(), size);
                successful += 1;
                ("success".to_string(), size)
            }
            Err(e) => {
                let duration = request_start.elapsed();
                println!("❌ FAILED ({}ms): {}", duration.as_millis(), e);
                failed += 1;
                (format!("error: {}", e), 0)
            }
        };
        
        records.push(RequestRecord {
            request_id: request_id.to_string(),
            timestamp: Utc::now().to_rfc3339(),
            endpoint: api_endpoint.clone(),
            duration_ms: request_start.elapsed().as_millis() as u64,
            status: status_str,
            response_size,
        });
    }

    let end_time = Utc::now();
    let total_duration = overall_start.elapsed();

    println!("{}", "-".repeat(80));
    println!("\n📊 Execution Summary:");
    println!("  Total Requests: {}", num_requests);
    
    let success_pct = if num_requests > 0 {
        (successful * 100) / num_requests
    } else {
        0
    };
    let failed_pct = if num_requests > 0 {
        (failed * 100) / num_requests
    } else {
        0
    };
    
    println!("  Successful: {} ({}%)", successful, success_pct);
    println!("  Failed: {} ({}%)", failed, failed_pct);
    println!("  Total Duration: {:.2}s", total_duration.as_secs_f64());
    
    let effective_rate = if total_duration.as_secs_f64() > 0.0 {
        num_requests as f64 / total_duration.as_secs_f64()
    } else {
        0.0
    };
    println!("  Effective Rate: {:.2} req/s", effective_rate);
    println!();

    // Create execution summary
    let summary = ExecutionSummary {
        run_id: run_id.clone(),
        start_time: start_time.to_rfc3339(),
        end_time: end_time.to_rfc3339(),
        total_requests: num_requests,
        successful_requests: successful,
        failed_requests: failed,
        total_duration_secs: total_duration.as_secs_f64(),
        rate_limit_config,
        requests: records,
    };

    // Save results to local file
    let output_dir = "/tmp/spcs_output";
    fs::create_dir_all(output_dir)
        .context("Failed to create output directory")?;
    
    let summary_filename = format!("api_results_{}.json", run_id);
    let summary_path = format!("{}/{}", output_dir, summary_filename);
    
    println!("💾 Saving results to local file...");
    let summary_json = serde_json::to_string_pretty(&summary)
        .context("Failed to serialize summary to JSON")?;
    fs::write(&summary_path, &summary_json)
        .context("Failed to write summary file")?;
    println!("  ✅ Saved to: {}", summary_path);
    println!();

    // Upload to Snowflake stage
    println!("☁️  Uploading results to Snowflake stage...");
    match upload_to_stage(&summary_path, &stage_path) {
        Ok(_) => {
            println!("  ✅ Successfully uploaded to {}/{}", stage_path, summary_filename);
            println!();
            println!("📁 To view the file in Snowflake, run:");
            println!("  LIST {};", stage_path);
            println!("  SELECT $1 FROM @api_results_stage/{} (FILE_FORMAT => (TYPE = JSON));", summary_filename);
        }
        Err(e) => {
            println!("  ⚠️  Upload failed: {}", e);
            println!("  (This is expected if not running in SPCS or stage not configured)");
        }
    }

    println!();
    println!("✅ Demo Complete!");
    println!("This service demonstrated:");
    println!("  ✓ Reading secrets from Snowflake-injected environment variables");
    println!("  ✓ Rate-limited API calls ({} req/s)", rate_limit_config.requests_per_second);
    println!("  ✓ Detailed request tracking and metrics");
    println!("  ✓ File persistence to local storage");
    println!("  ✓ Upload to Snowflake internal stage");

    Ok(())
}

async fn make_api_request(endpoint: &str, api_key: &str) -> Result<serde_json::Value> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(30))
        .build()?;

    let response = client
        .get(endpoint)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("User-Agent", "Snowflake-SPCS-Demo/2.0")
        .send()
        .await
        .context("Failed to send request")?;

    let status = response.status();

    if !status.is_success() {
        let error_text = response.text().await.unwrap_or_else(|_| "Unable to read error".to_string());
        anyhow::bail!("API returned error status {}: {}", status, error_text);
    }

    let body = response
        .json::<serde_json::Value>()
        .await
        .context("Failed to parse JSON response")?;

    Ok(body)
}

fn upload_to_stage(file_path: &str, stage_path: &str) -> Result<()> {
    // Upload file to Snowflake internal stage using PUT command
    // In SPCS, containers can use the Snowflake CLI or SQL to interact with stages
    // 
    // This uses the Snowflake CLI's stage put command to upload files.
    // The container must have the Snowflake CLI installed and configured.
    //
    // Alternative approach: Use SQL PUT via JDBC/ODBC driver
    
    let output = Command::new("snow")
        .args([
            "stage",
            "put",
            file_path,
            stage_path,
            "--overwrite",
        ])
        .output()
        .context("Failed to spawn snow CLI process")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        anyhow::bail!(
            "Stage upload failed with exit code {:?}\nStdout: {}\nStderr: {}",
            output.status.code(),
            stdout,
            stderr
        );
    }

    Ok(())
}

