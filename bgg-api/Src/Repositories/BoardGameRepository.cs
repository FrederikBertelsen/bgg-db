using BGGAPI.Src.Data;
using BGGAPI.Src.Entities;
using BGGAPI.Src.Repositories.Interfaces;
using Microsoft.EntityFrameworkCore;

namespace BGGAPI.Src.Repositories;

public class BoardGameRepository(AppDbContext dbContext) : IBoardGameRepository
{
    public async Task<BoardGame?> GetByIdAsync(int id) =>
        await dbContext.BoardGames
            .Include(bg => bg.Categories)
            .Include(bg => bg.Mechanics)
            .Include(bg => bg.Families)
            .Include(bg => bg.Types)
            .Include(bg => bg.Credits)
            .Include(bg => bg.Expansions)
            .Include(bg => bg.Reimplements)
            .Include(bg => bg.Ranks)
            .Include(bg => bg.Versions)
            .Include(bg => bg.ShopOffers)
            .Include(bg => bg.PlayerCountScores)
            .Include(bg => bg.RecommendationsFromThis)
                .ThenInclude(r => r.RecommendedBoardGame!)
                .ThenInclude(bg => bg.Ranks)
            .FirstOrDefaultAsync(bg => bg.Id == id);

    public async Task<IEnumerable<BoardGame>> GetByIdAsync(IEnumerable<int> ids) =>
        await dbContext.BoardGames
            .Where(bg => ids.ToList().Contains(bg.Id))
            .ToListAsync();

    public async Task<BoardGame?> GetCardByIdAsync(int id) =>
        await dbContext.BoardGames
            .Include(bg => bg.Ranks)
            .Where(bg => bg.Id == id)
            .FirstOrDefaultAsync();

    public async Task<IEnumerable<BoardGame>> GetCardsByIdAsync(IEnumerable<int> ids) =>
        await dbContext.BoardGames
            .Include(bg => bg.Ranks)
            .Where(bg => ids.Contains(bg.Id))
            .ToListAsync();
}