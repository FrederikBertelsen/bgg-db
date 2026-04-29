using BGGAPI.Src.Entities.Dtos;
using BGGAPI.Src.Services.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace BGGAPI.Src.Controllers;

[ApiController]
[Route("api/boardgames")]
public class BoardGameController(IBoardGameService boardGameService) : ControllerBase
{
    [HttpGet("{id}")]
    public async Task<ActionResult<BoardGameDto>> GetBoardGameById(int id)
    {
        var boardGame = await boardGameService.GetByIdAsync(id);
        return Ok(boardGame);
    }

    [HttpGet("card/{id}")]
    public async Task<ActionResult<BoardGameCardDto>> GetBoardGameCardById(int id)
    {
        var boardGameCard = await boardGameService.GetCardByIdAsync(id);
        return Ok(boardGameCard);
    }

    [HttpGet("cards")]
    public async Task<ActionResult<IEnumerable<BoardGameCardDto>>> GetBoardGamesByIds([FromQuery] IEnumerable<int> ids)
    {
        var boardGames = await boardGameService.GetCardsByIdAsync(ids);
        return Ok(boardGames);
    }
}