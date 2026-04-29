using BGGAPI.Src.Repositories.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace BGGAPI.Src.Controllers;

[ApiController]
[Route("api/dataloaders")]
public class DataLoaderController(IDataLoaderRepository dataLoaderRepository) : ControllerBase
{
    [HttpPost("load-latest-dataset")]
    public async Task<IActionResult> LoadLatestDataset() // (string apiKey)
    {
        // if (apiKey != "visibly-patchwork-unrefined-pedicure-straggler-exporter-straw-fifteen-vanilla-bronchial-starry-bonus-afraid-driving-vividly")
        //     return Unauthorized("Fuck OFF!");

        dataLoaderRepository.LoadLatestDatasetAsync();

        return Ok("Latest dataset loaded successfully.");
    }
}