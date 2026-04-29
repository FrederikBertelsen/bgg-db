using BGGAPI.Src.Entities.Dtos;
using BGGAPI.Src.Exceptions;
using BGGAPI.Src.Extensions;
using BGGAPI.Src.Repositories.Interfaces;
using BGGAPI.Src.Services.Interfaces;

namespace BGGAPI.Src.Services;

public class BoardGameService(IBoardGameRepository boardGameRepository) : IBoardGameService
{
    public async Task<BoardGameDto> GetByIdAsync(int id)
    {
        var foundBoardGame = await boardGameRepository.GetByIdAsync(id)
            ?? throw new NotFoundException("Board game", "ID", id);

        return foundBoardGame.ToDto();
    }

    public async Task<BoardGameDto> GetCardByIdAsync(int id)
    {
        var foundBoardGame = await boardGameRepository.GetCardByIdAsync(id)
            ?? throw new NotFoundException("Board game", "ID", id);
        
        return foundBoardGame.ToDto();
    }

    public async Task<IEnumerable<BoardGameDto>> GetCardsByIdAsync(IEnumerable<int> ids)
    {
        var foundBoardGames = await boardGameRepository.GetCardsByIdAsync(ids);

        if (!foundBoardGames.Any())
            throw new NotFoundException("Board games", "IDs", string.Join(", ", ids));
            
        return foundBoardGames.Select(bg => bg.ToDto());
    }
}